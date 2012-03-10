# -*- coding: utf-8 -*-


import time
import gevent.pool
import gevent.queue
import gevent.event
import gevent.local
import gevent.coros

from .exceptions import *
from .context import Context
from .events import Events


class SocketOnChannel(object):

    def __init__(self, channel, heartbeat=5, inqueue_size=100,
            passive_heartbeat=False):
        self._channel = channel
        self._heartbeat_freq = heartbeat
        self._input_queue_size = inqueue_size
        self._remote_queue_open_slots = 1
        self._input_queue_reserved = 1
        self._remote_last_hb = None
        self._remote_can_recv = gevent.event.Event()
        self._input_queue = gevent.queue.Queue()
        self._lost_remote = False
        self._aggressive_heartbeat = False
        self._recv_task = gevent.spawn(self._recver)
        self._parent_coroutine = None
        self._heartbeat_task = None
        if not passive_heartbeat:
            self._start_heartbeat()

    def __del__(self):
        self.close()

    def close(self):
        if self._heartbeat_task:
            self._heartbeat_task.kill()
        if self._recv_task:
            self._recv_task.kill()

    def _emit_heartbeat(self):
        open_slots = self._input_queue_size - self._input_queue_reserved
        self._input_queue_reserved += open_slots
        self._channel.emit('_zpc_hb', (open_slots,))

    def _heartbeat(self):
        while True:
            gevent.sleep(self._heartbeat_freq)
            if self._remote_last_hb is None:
                self._remote_last_hb = time.time()
            if time.time() > self._remote_last_hb + self._heartbeat_freq * 2:
                self._lost_remote = True
                gevent.kill(self._parent_coroutine,
                        self._lost_remote_exception())
                break
            self._emit_heartbeat()

    def _start_heartbeat(self):
        if self._heartbeat_task is None and self._heartbeat_freq is not None:
            self._parent_coroutine = gevent.getcurrent()
            self._heartbeat_task = gevent.spawn(self._heartbeat)

    def _recver(self):
        while True:
            event = self._channel.recv()
            if event.name == '_zpc_hb':
                self._remote_last_hb = time.time()
                self._start_heartbeat()
                try:
                    self._remote_queue_open_slots += int(event.args[0])
                except Exception as e:
                    print >> sys.stderr, \
                            'gevent_zerorpc.SocketOnChannel._recver,', \
                            'exception:', e
                if self._remote_queue_open_slots > 0:
                    self._remote_can_recv.set()
            elif self._input_queue.qsize() == self._input_queue_size:
                raise RuntimeError(
                        'SocketOnChannel, queue overflow on event:', event)
            else:
                self._input_queue.put(event)

    def emit(self, name, args, xheader={}, block=True, timeout=None):
        if self._lost_remote:
            raise self._lost_remote_exception()
        if self._remote_queue_open_slots == 0:
            if not block:
                return False
            self._remote_can_recv.clear()
            self._remote_can_recv.wait(timeout=timeout)
        self._remote_queue_open_slots -= 1
        try:
            self._channel.emit(name, args, xheader)
        except:
            self._remote_queue_open_slots += 1
            raise
        return True

    def _lost_remote_exception(self):
        return LostRemote('Lost remote after {0}s heartbeat'.format(
            self._heartbeat_freq * 2))

    def recv(self, timeout=None):
        if self._lost_remote:
            raise self._lost_remote_exception()

        if self._aggressive_heartbeat:
            self._start_heartbeat()
            if self._input_queue_reserved < self._input_queue_size / 2:
                self._emit_heartbeat()
        else:
            self._aggressive_heartbeat = True

        try:
            event = self._input_queue.get(timeout=timeout)
        except gevent.queue.Empty:
            raise TimeoutExpired(timeout)

        self._input_queue_reserved -= 1
        return event

    @property
    def channel(self):
        return self._channel


class SocketBase(object):

    def __init__(self, zmq_socket_type, context=None):
        self._context = context or Context.get_instance()
        self._events = Events(zmq_socket_type, context)

    def __del__(self):
        self.close()

    def close(self):
        self._events.close()

    def connect(self, endpoint, resolve=True):
        return self._events.connect(endpoint, resolve)

    def bind(self, endpoint, resolve=True):
        return self._events.bind(endpoint, resolve)
