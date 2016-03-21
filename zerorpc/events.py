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


import msgpack
import gevent.pool
import gevent.queue
import gevent.event
import gevent.local
import gevent.lock
import logging
import sys

import gevent_zmq as zmq
from .exceptions import TimeoutExpired
from .context import Context
from .channel_base import ChannelBase


if sys.version_info < (2, 7):
    def get_pyzmq_frame_buffer(frame):
        return frame.buffer[:]
else:
    def get_pyzmq_frame_buffer(frame):
        return frame.buffer


logger = logging.getLogger(__name__)


class SequentialSender(object):

    def __init__(self, socket):
        self._socket = socket

    def _send(self, parts):
        e = None
        for i in xrange(len(parts) - 1):
            try:
                self._socket.send(parts[i], copy=False, flags=zmq.SNDMORE)
            except (gevent.GreenletExit, gevent.Timeout) as e:
                if i == 0:
                    raise
                self._socket.send(parts[i], copy=False, flags=zmq.SNDMORE)
        try:
            self._socket.send(parts[-1], copy=False)
        except (gevent.GreenletExit, gevent.Timeout) as e:
            self._socket.send(parts[-1], copy=False)
        if e:
            raise e

    def __call__(self, parts, timeout=None):
        if timeout:
            with gevent.Timeout(timeout):
                self._send(parts)
        else:
            self._send(parts)


class SequentialReceiver(object):

    def __init__(self, socket):
        self._socket = socket

    def _recv(self):
        e = None
        parts = []
        while True:
            try:
                part = self._socket.recv(copy=False)
            except (gevent.GreenletExit, gevent.Timeout) as e:
                if len(parts) == 0:
                    raise
                part = self._socket.recv(copy=False)
            parts.append(part)
            if not part.more:
                break
        if e:
            raise e
        return parts

    def __call__(self, timeout=None):
        if timeout:
            with gevent.Timeout(timeout):
                return self._recv()
        else:
            return self._recv()


class Sender(SequentialSender):

    def __init__(self, socket):
        self._socket = socket
        self._send_queue = gevent.queue.Channel()
        self._send_task = gevent.spawn(self._sender)

    def close(self):
        if self._send_task:
            self._send_task.kill()

    def _sender(self):
        for parts in self._send_queue:
            super(Sender, self)._send(parts)

    def __call__(self, parts, timeout=None):
        try:
            self._send_queue.put(parts, timeout=timeout)
        except gevent.queue.Full:
            raise TimeoutExpired(timeout)


class Receiver(SequentialReceiver):

    def __init__(self, socket):
        self._socket = socket
        self._recv_queue = gevent.queue.Channel()
        self._recv_task = gevent.spawn(self._recver)

    def close(self):
        if self._recv_task:
            self._recv_task.kill()
        self._recv_queue = None

    def _recver(self):
        while True:
            parts = super(Receiver, self)._recv()
            self._recv_queue.put(parts)

    def __call__(self, timeout=None):
        try:
            return self._recv_queue.get(timeout=timeout)
        except gevent.queue.Empty:
            raise TimeoutExpired(timeout)


class Event(object):

    __slots__ = ['_name', '_args', '_header', '_identity']

    def __init__(self, name, args, context, header=None):
        self._name = name
        self._args = args
        if header is None:
            self._header = {'message_id': context.new_msgid(), 'v': 3}
        else:
            self._header = header
        self._identity = None

    @property
    def header(self):
        return self._header

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, v):
        self._name = v

    @property
    def args(self):
        return self._args

    @property
    def identity(self):
        return self._identity

    @identity.setter
    def identity(self, v):
        self._identity = v

    def pack(self):
        return msgpack.Packer(use_bin_type=True).pack((self._header, self._name, self._args))

    @staticmethod
    def unpack(blob):
        unpacker = msgpack.Unpacker(encoding='utf-8')
        unpacker.feed(blob)
        unpacked_msg = unpacker.unpack()

        try:
            (header, name, args) = unpacked_msg
        except Exception as e:
            raise Exception('invalid msg format "{0}": {1}'.format(
                unpacked_msg, e))

        # Backward compatibility
        if not isinstance(header, dict):
            header = {}

        return Event(name, args, None, header)

    def __str__(self, ignore_args=False):
        if ignore_args:
            args = '[...]'
        else:
            args = self._args
            try:
                args = '<<{0}>>'.format(str(self.unpack(self._args)))
            except Exception:
                pass
        if self._identity:
            identity = ', '.join(repr(x.bytes) for x in self._identity)
            return '<{0}> {1} {2} {3}'.format(identity, self._name,
                    self._header, args)
        return '{0} {1} {2}'.format(self._name, self._header, args)


class Events(ChannelBase):
    def __init__(self, zmq_socket_type, context=None):
        self._debug = False
        self._zmq_socket_type = zmq_socket_type
        self._context = context or Context.get_instance()
        self._socket = self._context.socket(zmq_socket_type)

        if zmq_socket_type in (zmq.PUSH, zmq.PUB, zmq.DEALER, zmq.ROUTER):
            self._send = Sender(self._socket)
        elif zmq_socket_type in (zmq.REQ, zmq.REP):
            self._send = SequentialSender(self._socket)
        else:
            self._send = None

        if zmq_socket_type in (zmq.PULL, zmq.SUB, zmq.DEALER, zmq.ROUTER):
            self._recv = Receiver(self._socket)
        elif zmq_socket_type in (zmq.REQ, zmq.REP):
            self._recv = SequentialReceiver(self._socket)
        else:
            self._recv = None

    @property
    def recv_is_supported(self):
        return self._recv is not None

    @property
    def emit_is_supported(self):
        return self._send is not None

    def __del__(self):
        try:
            if not self._socket.closed:
                self.close()
        except (AttributeError, TypeError):
            pass

    def close(self):
        try:
            self._send.close()
        except AttributeError:
            pass
        try:
            self._recv.close()
        except AttributeError:
            pass
        self._socket.close()

    @property
    def debug(self):
        return self._debug

    @debug.setter
    def debug(self, v):
        if v != self._debug:
            self._debug = v
            if self._debug:
                logger.debug('debug enabled')
            else:
                logger.debug('debug disabled')

    def _resolve_endpoint(self, endpoint, resolve=True):
        if resolve:
            endpoint = self._context.hook_resolve_endpoint(endpoint)
        if isinstance(endpoint, (tuple, list)):
            r = []
            for sub_endpoint in endpoint:
                r.extend(self._resolve_endpoint(sub_endpoint, resolve))
            return r
        return [endpoint]

    def connect(self, endpoint, resolve=True):
        r = []
        for endpoint_ in self._resolve_endpoint(endpoint, resolve):
            r.append(self._socket.connect(endpoint_))
            logger.debug('connected to %s (status=%s)', endpoint_, r[-1])
        return r

    def bind(self, endpoint, resolve=True):
        r = []
        for endpoint_ in self._resolve_endpoint(endpoint, resolve):
            r.append(self._socket.bind(endpoint_))
            logger.debug('bound to %s (status=%s)', endpoint_, r[-1])
        return r

    def disconnect(self, endpoint, resolve=True):
        r = []
        for endpoint_ in self._resolve_endpoint(endpoint, resolve):
            r.append(self._socket.disconnect(endpoint_))
            logging.debug('disconnected from %s (status=%s)', endpoint_, r[-1])
        return r

    def new_event(self, name, args, xheader=None):
        event = Event(name, args, context=self._context)
        if xheader:
            event.header.update(xheader)
        return event

    def emit_event(self, event, timeout=None):
        if self._debug:
            logger.debug('--> %s', event)
        if event.identity:
            parts = list(event.identity or list())
            parts.extend(['', event.pack()])
        elif self._zmq_socket_type in (zmq.DEALER, zmq.ROUTER):
            parts = ('', event.pack())
        else:
            parts = (event.pack(),)
        self._send(parts, timeout)

    def recv(self, timeout=None):
        parts = self._recv(timeout=timeout)
        if len(parts) > 2:
            identity = parts[0:-2]
            blob = parts[-1]
        elif len(parts) == 2:
            identity = parts[0:-1]
            blob = parts[-1]
        else:
            identity = None
            blob = parts[0]
        event = Event.unpack(get_pyzmq_frame_buffer(blob))
        event.identity = identity
        if self._debug:
            logger.debug('<-- %s', event)
        return event

    def setsockopt(self, *args):
        return self._socket.setsockopt(*args)

    @property
    def context(self):
        return self._context
