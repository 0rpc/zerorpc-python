# -*- coding: utf-8 -*-


import msgpack
import gevent.pool
import gevent.queue
import gevent.event
import gevent.local
import gevent.coros


import gevent_zmq as zmq
from .context import Context


class Sender(object):

    def __init__(self, socket):
        self._socket = socket
        self._send_queue = gevent.queue.Queue(maxsize=0)
        self._send_task = gevent.spawn(self._sender)

    def __del__(self):
        self.close()

    def close(self):
        if self._send_task:
            self._send_queue.kill()

    def _sender(self):
        running = True
        for parts in self._send_queue:
            for i in xrange(len(parts) - 1):
                try:
                    self._socket.send(parts[i], flags=zmq.SNDMORE)
                except gevent.GreenletExit:
                    if i == 0:
                        return
                    running = False
                    self._socket.send(parts[i], flags=zmq.SNDMORE)
            self._socket.send(parts[-1])
            if not running:
                return

    def __call__(self, parts):
        self._send_queue.put(parts)


class Receiver(object):

    def __init__(self, socket):
        self._socket = socket
        self._recv_queue = gevent.queue.Queue(maxsize=0)
        self._recv_task = gevent.spawn(self._recver)

    def __del__(self):
        self.close()

    def close(self):
        if self._recv_task:
            self._recv_task.kill()

    def _recver(self):
        running = True
        while True:
            parts = []
            while True:
                try:
                    part = self._socket.recv()
                except gevent.GreenletExit:
                    running = False
                    if len(parts) == 0:
                        return
                    part = self._socket.recv()
                parts.append(part)
                if not self._socket.getsockopt(zmq.RCVMORE):
                    break
            if not running:
                break
            self._recv_queue.put(parts)

    def __call__(self):
        return self._recv_queue.get()


class Event(object):

    def __init__(self, name, args, context, header=None):
        self._name = name
        self._args = args
        if header is None:
            context = context or Context.get_instance()
            self._header = {
                    'message_id': context.new_msgid(),
                    'v': 2
                    }
        else:
            self._header = header

    @property
    def header(self):
        return self._header

    @property
    def name(self):
        return self._name

    @property
    def args(self):
        return self._args

    def pack(self):
        return msgpack.Packer().pack((self._header, self._name, self._args))

    @staticmethod
    def unpack(blob):
        unpacker = msgpack.Unpacker()
        unpacker.feed(blob)
        (header, name, args) = unpacker.unpack()

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
            except:
                pass
        return '{0} {1} {2}'.format(self._name, self._header,
                args)


class Events(object):
    def __init__(self, zmq_socket_type, context=None):
        self._zmq_socket_type = zmq_socket_type
        self._context = context or Context.get_instance()
        self._socket = zmq.Socket(self._context, zmq_socket_type)
        self._send = self._socket.send_multipart
        self._recv = self._socket.recv_multipart
        if zmq_socket_type in (zmq.PUSH, zmq.PUB, zmq.XREQ, zmq.XREP):
            self._send = Sender(self._socket)
        if zmq_socket_type in (zmq.PULL, zmq.SUB, zmq.XREQ, zmq.XREP):
            self._recv = Receiver(self._socket)

    @property
    def recv_is_available(self):
        return self._zmq_socket_type in (zmq.PULL, zmq.SUB, zmq.XREQ, zmq.XREP)

    def __del__(self):
        if not self._socket.closed:
            self.close()

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

    def _resolve_endpoint(self, endpoint, resolve=True):
        if resolve:
            endpoint = self._context.middleware_resolve_endpoint(endpoint)
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
        return r

    def bind(self, endpoint, resolve=True):
        r = []
        for endpoint_ in self._resolve_endpoint(endpoint, resolve):
            r.append(self._socket.bind(endpoint_))
        return r

    def create_event(self, name, args, xheader={}):
        event = Event(name, args, context=self._context)
        for k, v in xheader.items():
            if k == 'zmqid':
                continue
            event.header[k] = v
        return event

    def emit_event(self, event, identity=None):
        if identity is not None:
            parts = list(identity)
            parts.extend(['', event.pack()])
        elif self._zmq_socket_type in (zmq.XREQ, zmq.XREP):
            parts = ('', event.pack())
        else:
            parts = (event.pack(),)
        self._send(parts)

    def emit(self, name, args, xheader={}):
        event = self.create_event(name, args, xheader)
        identity = xheader.get('zmqid', None)
        return self.emit_event(event, identity)

    def recv(self):
        parts = self._recv()
        if len(parts) == 1:
            identity = None
            blob = parts[0]
        else:
            identity = parts[0:-2]
            blob = parts[-1]
        event = Event.unpack(blob)
        if identity is not None:
            event.header['zmqid'] = identity
        return event

    def setsockopt(self, *args):
        return self._socket.setsockopt(*args)


class WrappedEvents(object):
    def __init__(self, channel):
        self._channel = channel

    @property
    def recv_is_available(self):
        return self._channel.recv_is_available

    def create_event(self, name, args, xheader={}):
        wrapped_event = Event(name, args, None)
        wrapped_event.header.update(xheader)
        return wrapped_event

    def emit_event(self, event, identity=None):
        return self._channel.emit('w', event.pack())

    def emit(self, name, args, xheader={}):
        wrapped_event = self.create_event(name, args, xheader)
        return self._channel.emit('w', wrapped_event.pack())

    def recv(self, timeout=None):
        event = self._channel.recv()
        wrapped_event = Event.unpack(event.args)
        return wrapped_event
