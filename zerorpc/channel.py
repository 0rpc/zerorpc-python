# -*- coding: utf-8 -*-
# Open Source Initiative OSI - The MIT License (MIT):Licensing
#
# The MIT License (MIT)
# Copyright (c) 2015 François-Xavier Bourlet (bombela+zerorpc@gmail.com)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import gevent.pool
import gevent.queue
import gevent.event
import gevent.local
import gevent.lock
import logging

from .exceptions import TimeoutExpired
from .channel_base import ChannelBase

from logging import getLogger

logger = getLogger(__name__)


class ChannelMultiplexer(ChannelBase):
    def __init__(self, events, ignore_broadcast=False):
        self._events = events
        self._active_channels = {}
        self._channel_dispatcher_task = None
        self._broadcast_queue = None
        if events.recv_is_supported and not ignore_broadcast:
            self._broadcast_queue = gevent.queue.Queue(maxsize=1)
            self._channel_dispatcher_task = gevent.spawn(
                self._channel_dispatcher)

    @property
    def recv_is_supported(self):
        return self._events.recv_is_supported

    @property
    def emit_is_supported(self):
        return self._events.emit_is_supported

    def close(self):
        if self._channel_dispatcher_task:
            self._channel_dispatcher_task.kill()

    def new_event(self, name, args, xheader=None):
        return self._events.new_event(name, args, xheader)

    def emit_event(self, event, timeout=None):
        return self._events.emit_event(event, timeout)

    def recv(self, timeout=None):
        if self._broadcast_queue is not None:
            event = self._broadcast_queue.get(timeout=timeout)
        else:
            event = self._events.recv(timeout=timeout)
        return event

    def _channel_dispatcher(self):
        while True:
            try:
                event = self._events.recv()
            except Exception:
                logger.exception('zerorpc.ChannelMultiplexer ignoring error on recv')
                continue
            channel_id = event.header.get('response_to', None)

            queue = None
            if channel_id is not None:
                channel = self._active_channels.get(channel_id, None)
                if channel is not None:
                    queue = channel._queue
            elif self._broadcast_queue is not None:
                queue = self._broadcast_queue

            if queue is None:
                logger.warning('zerorpc.ChannelMultiplexer,'
                        ' unable to route event: {0}'.format(
                            event.__str__(ignore_args=True)))
            else:
                queue.put(event)

    def channel(self, from_event=None):
        if self._channel_dispatcher_task is None:
            self._channel_dispatcher_task = gevent.spawn(
                self._channel_dispatcher)
        return Channel(self, from_event)

    @property
    def active_channels(self):
        return self._active_channels

    @property
    def context(self):
        return self._events.context


class Channel(ChannelBase):

    def __init__(self, multiplexer, from_event=None):
        self._multiplexer = multiplexer
        self._channel_id = None
        self._zmqid = None
        self._queue = gevent.queue.Queue(maxsize=1)
        if from_event is not None:
            self._channel_id = from_event.header['message_id']
            self._zmqid = from_event.identity
            self._multiplexer._active_channels[self._channel_id] = self
            logging.debug('<-- new channel %s', self._channel_id)
            self._queue.put(from_event)

    @property
    def recv_is_supported(self):
        return self._multiplexer.recv_is_supported

    @property
    def emit_is_supported(self):
        return self._multiplexer.emit_is_supported

    def close(self):
        if self._channel_id is not None:
            del self._multiplexer._active_channels[self._channel_id]
            logging.debug('-x- closed channel %s', self._channel_id)
            self._channel_id = None

    def new_event(self, name, args, xheader=None):
        event = self._multiplexer.new_event(name, args, xheader)
        if self._channel_id is None:
            self._channel_id = event.header['message_id']
            self._multiplexer._active_channels[self._channel_id] = self
            logging.debug('--> new channel %s', self._channel_id)
        else:
            event.header['response_to'] = self._channel_id
        event.identity = self._zmqid
        return event

    def emit_event(self, event, timeout=None):
        self._multiplexer.emit_event(event, timeout)

    def recv(self, timeout=None):
        try:
            event = self._queue.get(timeout=timeout)
        except gevent.queue.Empty:
            raise TimeoutExpired(timeout)
        return event

    @property
    def context(self):
        return self._multiplexer.context


class BufferedChannel(ChannelBase):

    def __init__(self, channel, inqueue_size=100):
        self._channel = channel
        self._input_queue_size = inqueue_size
        self._remote_queue_open_slots = 1
        self._input_queue_reserved = 1
        self._remote_can_recv = gevent.event.Event()
        self._input_queue = gevent.queue.Queue()
        self._verbose = False
        self._on_close_if = None
        self._recv_task = gevent.spawn(self._recver)

    @property
    def recv_is_supported(self):
        return self._channel.recv_is_supported

    @property
    def emit_is_supported(self):
        return self._channel.emit_is_supported

    @property
    def on_close_if(self):
        return self._on_close_if

    @on_close_if.setter
    def on_close_if(self, cb):
        self._on_close_if = cb

    def close(self):
        if self._recv_task is not None:
            self._recv_task.kill()
            self._recv_task = None
        if self._channel is not None:
            self._channel.close()
            self._channel = None

    def _recver(self):
        while True:
            event = self._channel.recv()
            if event.name == '_zpc_more':
                try:
                    self._remote_queue_open_slots += int(event.args[0])
                except Exception:
                    logger.exception('gevent_zerorpc.BufferedChannel._recver')
                if self._remote_queue_open_slots > 0:
                    self._remote_can_recv.set()
            elif self._input_queue.qsize() == self._input_queue_size:
                raise RuntimeError(
                    'BufferedChannel, queue overflow on event:', event)
            else:
                self._input_queue.put(event)
                if self._on_close_if is not None and self._on_close_if(event):
                    self._recv_task = None
                    self.close()
                    return

    def new_event(self, name, args, xheader=None):
        return self._channel.new_event(name, args, xheader)

    def emit_event(self, event, timeout=None):
        if self._remote_queue_open_slots == 0:
            self._remote_can_recv.clear()
            self._remote_can_recv.wait(timeout=timeout)
        self._remote_queue_open_slots -= 1
        try:
            self._channel.emit_event(event)
        except:
            self._remote_queue_open_slots += 1
            raise

    def _request_data(self):
        open_slots = self._input_queue_size - self._input_queue_reserved
        self._input_queue_reserved += open_slots
        self._channel.emit('_zpc_more', (open_slots,))

    def recv(self, timeout=None):
        if self._verbose:
            if self._input_queue_reserved < self._input_queue_size / 2:
                self._request_data()
        else:
            self._verbose = True

        try:
            event = self._input_queue.get(timeout=timeout)
        except gevent.queue.Empty:
            raise TimeoutExpired(timeout)

        self._input_queue_reserved -= 1
        return event

    @property
    def channel(self):
        return self._channel

    @property
    def context(self):
        return self._channel.context
