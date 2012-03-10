# -*- coding: utf-8 -*-
# Open Source Initiative OSI - The MIT License (MIT):Licensing
#
# The MIT License (MIT)
# Copyright (c) 2012 DotCloud Inc (opensource@dotcloud.com)
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


import inspect
import msgpack
import uuid
import time
import sys
import traceback
import gevent.pool
import gevent.queue
import gevent.event
import gevent.local
import gevent.coros

import gevent_zmq as zmq


class LostRemote(Exception):
    pass

class TimeoutExpired(Exception):

    def __init__(self, timeout_s, when=None):
        msg = 'timeout after {0}s'
        if when:
            msg = '{0}, when {1}'.format(msg, when)
        super(TimeoutExpired, self).__init__(msg)

class RemoteError(Exception):

    def __init__(self, name, human_msg, human_traceback):
        self.name = name
        self.msg = human_msg
        self.traceback = human_traceback

    def __str__(self):
        if self.traceback is not None:
            return self.traceback
        return '{0}: {1}'.format(self.name, self.msg)


class Context(zmq.Context):
    _instance = None

    def __init__(self):
        self._middlewares = []
        self._middlewares_hooks = {
                'resolve_endpoint': [],
                'raise_error': []
                }

    @staticmethod
    def get_instance():
        if Context._instance is None:
            Context._instance = Context()
        return Context._instance

    def new_msgid(self):
        return str(uuid.uuid4())

    def register_middleware(self, middleware_instance):
        registered_count = 0
        self._middlewares.append(middleware_instance)
        for hook in self._middlewares_hooks.keys():
            functor = getattr(middleware_instance, hook, None)
            if functor is None:
                try:
                    functor = middleware_instance.get(hook, None)
                except AttributeError:
                    pass
            if functor is not None:
                self._middlewares_hooks[hook].append(functor)
                registered_count += 1
        return registered_count

    def middleware_resolve_endpoint(self, endpoint):
        for functor in self._middlewares_hooks['resolve_endpoint']:
            endpoint = functor(endpoint)
        return endpoint

    def middleware_raise_error(self, event):
        for functor in self._middlewares_hooks['raise_error']:
            functor(event)


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


class ChannelMultiplexer(object):
    def __init__(self, events, ignore_broadcast=False):
        self._events = events
        self._active_channels = {}
        self._channel_dispatcher_task = None
        self._broadcast_queue = None
        if events.recv_is_available and not ignore_broadcast:
            self._broadcast_queue = gevent.queue.Queue(maxsize=1)
            self._channel_dispatcher_task = gevent.spawn(self._channel_dispatcher)

    @property
    def recv_is_available(self):
        return self._events.recv_is_available

    def __del__(self):
        self.close()

    def close(self):
        if self._channel_dispatcher_task:
            self._channel_dispatcher_task.kill()

    def create_event(self, name, args, xheader={}):
        return self._events.create_event(name, args, xheader)

    def emit_event(self, event, identity=None):
        return self._events.emit_event(event, identity)

    def emit(self, name, args, xheader={}):
        return self._events.emit(name, args, xheader)

    def recv(self):
        if self._broadcast_queue is not None:
            event = self._broadcast_queue.get()
        else:
            event = self._events.recv()
        return event

    def _channel_dispatcher(self):
        while True:
            event = self._events.recv()
            channel_id = event.header.get('response_to', None)

            queue = None
            if channel_id is not None:
                channel = self._active_channels.get(channel_id, None)
                if channel is not None:
                    queue = channel._queue
            elif self._broadcast_queue is not None:
                queue = self._broadcast_queue

            if queue is None:
                print >> sys.stderr, \
                        'zerorpc.ChannelMultiplexer, ', \
                        'unable to route event:', \
                        event.__str__(ignore_args=True)
            else:
                queue.put(event)

    def channel(self, from_event=None):
        if self._channel_dispatcher_task is None:
            self._channel_dispatcher_task = gevent.spawn(self._channel_dispatcher)
        return Channel(self, from_event)

    @property
    def active_channels(self):
        return self._active_channels


class Channel(object):

    def __init__(self, multiplexer, from_event=None):
        self._multiplexer = multiplexer
        self._channel_id = None
        self._zmqid = None
        self._queue = gevent.queue.Queue(maxsize=1)
        if from_event is not None:
            self._channel_id = from_event.header['message_id']
            self._zmqid = from_event.header.get('zmqid', None)
            self._multiplexer._active_channels[self._channel_id] = self
            self._queue.put(from_event)

    @property
    def recv_is_available(self):
        return self._multiplexer.recv_is_available

    def __del__(self):
        self.close()

    def close(self):
        if self._channel_id is not None:
            del self._multiplexer._active_channels[self._channel_id]
            self._channel_id = None

    def emit(self, name, args, xheader={}):
        event = self._multiplexer.create_event(name, args, xheader)

        if self._channel_id is None:
            self._channel_id = event.header['message_id']
            self._multiplexer._active_channels[self._channel_id] = self
        else:
            event.header['response_to'] = self._channel_id

# TODO debug middleware
#        print time.time(), 'channel emit', event
        self._multiplexer.emit_event(event, self._zmqid)

    def recv(self, timeout=None):
        try:
            event = self._queue.get(timeout=timeout)
        except gevent.queue.Empty:
            raise TimeoutExpired(timeout)
# TODO debug middleware
#        print time.time(), 'channel recv', event
        return event


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


class DecoratorBase(object):
    pattern = None

    def __init__(self, functor):
        self._functor = functor
        self.__doc__ = functor.__doc__
        self.__name__ = functor.__name__

    def __get__(self, instance, type_instance=None):
        if instance is None:
            return self
        return self.__class__(self._functor.__get__(instance, type_instance))

    def __call__(self, *args, **kargs):
        return self._functor(*args, **kargs)

    def _zerorpc_args(self):
        try:
            args_spec = self._functor._zerorpc_args()
        except AttributeError:
            try:
                args_spec = inspect.getargspec(self._functor)
            except TypeError:
                try:
                    args_spec = inspect.getargspec(self._functor.__call__)
                except (AttributeError, TypeError):
                    args_spec = None
        return args_spec


class PatternReqRep():

    def process_call(self, socket, event, functor):
        result = functor(*event.args)
        socket.emit('OK', (result,))

    def accept_answer(self, event):
        return True

    def process_answer(self, socket, event, method, timeout,
        raise_remote_error):
        result = event.args[0]
        if event.name == 'ERR':
            raise_remote_error(event)
        socket.close()
        socket.channel.close()
        return result


class rep(DecoratorBase):
    pattern = PatternReqRep()


class PatternReqStream():

    def process_call(self, socket, event, functor):
        for result in iter(functor(*event.args)):
            socket.emit('STREAM', result)
        socket.emit('STREAM_DONE', None)

    def accept_answer(self, event):
        return event.name in ('STREAM', 'STREAM_DONE')

    def process_answer(self, socket, event, method, timeout,
            raise_remote_error):
        def iterator(event):
            while event.name == 'STREAM':
                yield event.args
                event = socket.recv()
            if event.name == 'ERR':
                raise_remote_error(event)
            socket.close()
            socket.channel.close()
        return iterator(event)


class stream(DecoratorBase):
    pattern = PatternReqStream()


class Server(SocketBase):
    def __init__(self, methods=None, name=None, context=None, pool_size=None,
            heartbeat=5):
        super(Server, self).__init__(zmq.XREP, context)
        self._multiplexer = ChannelMultiplexer(self._events)

        if methods is None:
            methods = self

        self._name = name or repr(methods)
        self._task_pool = gevent.pool.Pool(size=pool_size)
        self._acceptor_task = None

        if hasattr(methods, '__getitem__'):
            self._methods = methods
        else:
            server_methods = set(getattr(self, k) for k in dir(Server) if not
                    k.startswith('_'))
            self._methods = dict((k, getattr(methods, k))
                    for k in dir(methods)
                    if callable(getattr(methods, k))
                    and not k.startswith('_')
                    and getattr(methods, k) not in server_methods
                    )

        self._inject_builtins()
        self._heartbeat_freq = heartbeat

        for (k, functor) in self._methods.items():
            if not isinstance(functor, DecoratorBase):
                self._methods[k] = rep(functor)

    def __del__(self):
        self.close()
        super(Server, self).__del__()

    def close(self):
        self.stop()
        self._multiplexer.close()
        super(Server, self).close()

    def _zerorpc_inspect(self, method=None, long_doc=True):
        if method:
            methods = { method: self._methods[method] }
        else:
            methods = dict((m, f) for m, f in self._methods.items()
                    if not m.startswith('_'))
        detailled_methods = [ (m, f._zerorpc_args(),
            f.__doc__ if long_doc else
            f.__doc__.split('\n', 1)[0] if f.__doc__ else None)
                for (m, f) in methods.items() ]
        return { 'name': self._name,
                'methods': detailled_methods }

    def _inject_builtins(self):
        self._methods['_zerorpc_list'] = lambda: [m for m in self._methods
                if not m.startswith('_')]
        self._methods['_zerorpc_name'] = lambda: self._name
        self._methods['_zerorpc_ping'] = lambda: ['pong', self._name]
        self._methods['_zerorpc_help'] = lambda m: self._methods[m].__doc__
        self._methods['_zerorpc_args'] = lambda m: self._methods[m]._zerorpc_args()
        self._methods['_zerorpc_inspect'] = self._zerorpc_inspect

    def __call__(self, method, *args):
        if method not in self._methods:
            raise NameError(method)
        return self._methods[method](*args)

    def _async_task(self, initial_event):
        protocol_v2 = initial_event.header.get('v', 1) >= 2
        channel = self._multiplexer.channel(initial_event)
        socket = SocketOnChannel(channel, heartbeat=self._heartbeat_freq,
                passive_heartbeat=not protocol_v2)
        event = socket.recv()
        try:
            functor = self._methods.get(event.name, None)
            if functor is None:
                raise NameError(event.name)
            functor.pattern.process_call(socket, event, functor)
        except Exception:
            try:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                traceback.print_exception(exc_type, exc_value, exc_traceback,
                        file=sys.stderr)
                human_traceback = traceback.format_exc()

                name = exc_type.__name__
                human_msg = str(exc_value)

                if protocol_v2:
                    socket.emit('ERR', (name, human_msg, human_traceback))
                else:
                    socket.emit('ERR', (repr(exc_value),))
            finally:
                del exc_traceback
        finally:
            socket.close()
            socket.channel.close()

    def _acceptor(self):
        while True:
            initial_event = self._multiplexer.recv()
            self._task_pool.spawn(self._async_task, initial_event)

    def run(self):
        self._acceptor_task = gevent.spawn(self._acceptor)
        try:
            self._acceptor_task.get()
        finally:
            self._acceptor_task = None
            self._task_pool.join(raise_error=True)

    def stop(self):
        if self._acceptor_task is not None:
            self._acceptor_task.kill(block=False)


class Client(SocketBase):
    patterns = [PatternReqStream(), PatternReqRep()]

    def __init__(self, context=None, timeout=30, heartbeat=5,
            passive_heartbeat=False):
        super(Client, self).__init__(zmq.XREQ, context=context)
        self._multiplexer = ChannelMultiplexer(self._events,
                ignore_broadcast=True)
        self._timeout = timeout
        self._heartbeat_freq = heartbeat
        self._passive_heartbeat = passive_heartbeat

    def __del__(self):
        self.close()
        super(Client, self).__del__()

    def close(self):
        self._multiplexer.close()
        super(Client, self).close()

    def _raise_remote_error(self, event):
        self._context.middleware_raise_error(event)

        if event.header.get('v', 1) >= 2:
            (name, msg, traceback) = event.args
            raise RemoteError(name, msg, traceback)
        else:
            (msg,) = event.args
            raise RemoteError('RemoteError', msg, None)

    def _select_pattern(self, event):
        for pattern in Client.patterns:
            if pattern.accept_answer(event):
                return pattern
        msg = 'Unable to find a pattern for: {0}'.format(event)
        raise RuntimeError(msg)

    def _process_response(self, method, socket, timeout):
        try:
            try:
                event = socket.recv(timeout)
            except TimeoutExpired:
                raise TimeoutExpired(timeout,
                        'calling remote method {0}'.format(method))

            pattern = self._select_pattern(event)
            return pattern.process_answer(socket, event, method, timeout,
                    self._raise_remote_error)
        except:
            socket.close()
            socket.channel.close()
            raise

    def __call__(self, method, *args, **kargs):
        timeout = kargs.get('timeout', self._timeout)
        channel = self._multiplexer.channel()
        socket = SocketOnChannel(channel, heartbeat=self._heartbeat_freq,
                passive_heartbeat=self._passive_heartbeat,
                inqueue_size=kargs.get('slots', 100))

        socket.emit(method, args)

        try:
            if kargs.get('async', False) is False:
                return self._process_response(method, socket, timeout)

            async_result = gevent.event.AsyncResult()
            gevent.spawn(self._process_response, method, socket,
                    timeout).link(async_result)
            return async_result
        except:
            socket.close()
            channel.close()
            raise

    def __getattr__(self, method):
        return lambda *args, **kargs: self(method, *args, **kargs)


class Pusher(SocketBase):

    def __init__(self, context=None, zmq_socket=zmq.PUSH):
        super(Pusher, self).__init__(zmq_socket, context=context)

    def __call__(self, method, *args):
        self._events.emit(method, args)

    def __getattr__(self, method):
        return lambda *args: self(method, *args)


class Puller(SocketBase):

    def __init__(self, methods=None, name=None, context=None,
            zmq_socket=zmq.PULL):
        super(Puller, self).__init__(zmq_socket, context=context)

        if methods is None:
            methods = self

        if hasattr(methods, '__getitem__'):
            self._methods = methods
        else:
            server_methods = set(getattr(self, k)
                    for k in dir(Pusher) if not k.startswith('_'))
            self._methods = dict((k, getattr(methods, k))
                    for k in dir(methods)
                    if callable(getattr(methods, k))
                    and not k.startswith('_')
                    and getattr(methods, k) not in server_methods
                    )

        self._receiver_task = None

    def close(self):
        self.stop()
        super(Pusher, self).close()

    def __call__(self, method, *args):
        if method not in self._methods:
            raise NameError(method)
        return self._methods[method](*args)

    def _receiver(self):
        while True:
            event = self._events.recv()
            try:
                if event.name not in self._methods:
                    raise NameError(event.name)
                self._methods[event.name](*event.args)
            except Exception:
                traceback.print_exc(file=sys.stderr)

    def run(self):
        self._receiver_task = gevent.spawn(self._receiver)
        try:
            self._receiver_task.get()
        finally:
            self._receiver_task = None

    def stop(self):
        if self._receiver_task is not None:
            self._receiver_task.kill(block=False)


class Publisher(Pusher):

    def __init__(self, context=None):
        super(Publisher, self).__init__(context=context, zmq_socket=zmq.PUB)


class Subscriber(Puller):

    def __init__(self, context=None):
        super(Subscriber, self).__init__(context=context, zmq_socket=zmq.SUB)
        self._events.setsockopt(zmq.SUBSCRIBE, '')
