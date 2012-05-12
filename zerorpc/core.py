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
import sys
import traceback
import gevent.pool
import gevent.queue
import gevent.event
import gevent.local
import gevent.coros

import gevent_zmq as zmq
from .exceptions import TimeoutExpired, RemoteError, LostRemote
from .channel import ChannelMultiplexer, BufferedChannel
from .socket import SocketBase
from .heartbeat import HeartBeatOnChannel
from .context import Context


class ServerBase(object):

    def __init__(self, channel, methods=None, name=None, context=None,
            pool_size=None, heartbeat=5):
        self._multiplexer = ChannelMultiplexer(channel)

        if methods is None:
            methods = self

        self._context = context or Context.get_instance()
        self._name = name or repr(methods)
        self._task_pool = gevent.pool.Pool(size=pool_size)
        self._acceptor_task = None
        self._methods = self._zerorpc_filter_methods(ServerBase, self, methods)

        self._inject_builtins()
        self._heartbeat_freq = heartbeat

        for (k, functor) in self._methods.items():
            if not isinstance(functor, DecoratorBase):
                self._methods[k] = rep(functor)

    @staticmethod
    def _zerorpc_filter_methods(cls, self, methods):
        if hasattr(methods, '__getitem__'):
            return methods
        server_methods = set(getattr(self, k) for k in dir(cls) if not
                k.startswith('_'))
        return dict((k, getattr(methods, k))
                for k in dir(methods)
                if callable(getattr(methods, k))
                and not k.startswith('_')
                and getattr(methods, k) not in server_methods
                )

    def close(self):
        self.stop()
        self._multiplexer.close()

    def _zerorpc_inspect(self, method=None, long_doc=True):
        if method:
            methods = {method: self._methods[method]}
        else:
            methods = dict((m, f) for m, f in self._methods.items()
                    if not m.startswith('_'))
        detailled_methods = [(m, f._zerorpc_args(),
            f.__doc__ if long_doc else
            f.__doc__.split('\n', 1)[0] if f.__doc__ else None)
                for (m, f) in methods.items()]
        return {'name': self._name,
                'methods': detailled_methods}

    def _inject_builtins(self):
        self._methods['_zerorpc_list'] = lambda: [m for m in self._methods
                if not m.startswith('_')]
        self._methods['_zerorpc_name'] = lambda: self._name
        self._methods['_zerorpc_ping'] = lambda: ['pong', self._name]
        self._methods['_zerorpc_help'] = lambda m: self._methods[m].__doc__
        self._methods['_zerorpc_args'] = \
            lambda m: self._methods[m]._zerorpc_args()
        self._methods['_zerorpc_inspect'] = self._zerorpc_inspect

    def __call__(self, method, *args):
        if method not in self._methods:
            raise NameError(method)
        return self._methods[method](*args)

    def _print_traceback(self, protocol_v1):
        exc_type, exc_value, exc_traceback = sys.exc_info()
        try:
            traceback.print_exception(exc_type, exc_value, exc_traceback,
                    file=sys.stderr)

            self._context.middleware_inspect_error(exc_type, exc_value,
                    exc_traceback)

            if protocol_v1:
                return (repr(exc_value),)

            human_traceback = traceback.format_exc()
            name = exc_type.__name__
            human_msg = str(exc_value)
            return (name, human_msg, human_traceback)
        finally:
            del exc_traceback

    def _async_task(self, initial_event):
        protocol_v1 = initial_event.header.get('v', 1) < 2
        channel = self._multiplexer.channel(initial_event)
        hbchan = HeartBeatOnChannel(channel, freq=self._heartbeat_freq,
                passive=protocol_v1)
        bufchan = BufferedChannel(hbchan)
        event = bufchan.recv()
        try:
            self._context.middleware_load_task_context(event.header)
            functor = self._methods.get(event.name, None)
            if functor is None:
                raise NameError(event.name)
            functor.pattern.process_call(self._context, bufchan, event, functor)
        except LostRemote:
            self._print_traceback(protocol_v1)
        except Exception:
            exception_info = self._print_traceback(protocol_v1)
            bufchan.emit('ERR', exception_info,
                    self._context.middleware_get_task_context())
        finally:
            bufchan.close()
            bufchan.channel.close()
            bufchan.channel.channel.close()

    def _acceptor(self):
        while True:
            initial_event = self._multiplexer.recv()
            self._task_pool.spawn(self._async_task, initial_event)

    def run(self):
        self._acceptor_task = gevent.spawn(self._acceptor)
        try:
            self._acceptor_task.get()
        finally:
            self.stop()
            self._task_pool.join(raise_error=True)

    def stop(self):
        if self._acceptor_task is not None:
            self._acceptor_task.kill()
            self._acceptor_task = None


class ClientBase(object):

    def __init__(self, channel, patterns, context=None, timeout=30, heartbeat=5,
            passive_heartbeat=False):
        self._multiplexer = ChannelMultiplexer(channel,
                ignore_broadcast=True)
        self._context = context or Context.get_instance()
        self._patterns = patterns
        self._timeout = timeout
        self._heartbeat_freq = heartbeat
        self._passive_heartbeat = passive_heartbeat

    def close(self):
        self._multiplexer.close()

    def _raise_remote_error(self, event):
        self._context.middleware_raise_error(event)

        if event.header.get('v', 1) >= 2:
            (name, msg, traceback) = event.args
            raise RemoteError(name, msg, traceback)
        else:
            (msg,) = event.args
            raise RemoteError('RemoteError', msg, None)

    def _select_pattern(self, event):
        for pattern in self._patterns:
            if pattern.accept_answer(event):
                return pattern
        msg = 'Unable to find a pattern for: {0}'.format(event)
        raise RuntimeError(msg)

    def _process_response(self, method, bufchan, timeout):
        try:
            try:
                event = bufchan.recv(timeout)
            except TimeoutExpired:
                raise TimeoutExpired(timeout,
                        'calling remote method {0}'.format(method))

            pattern = self._select_pattern(event)
            return pattern.process_answer(self._context, bufchan, event, method,
                timeout, self._raise_remote_error)
        except:
            bufchan.close()
            bufchan.channel.close()
            bufchan.channel.channel.close()
            raise

    def __call__(self, method, *args, **kargs):
        timeout = kargs.get('timeout', self._timeout)
        channel = self._multiplexer.channel()
        hbchan = HeartBeatOnChannel(channel, freq=self._heartbeat_freq,
                passive=self._passive_heartbeat)
        bufchan = BufferedChannel(hbchan, inqueue_size=kargs.get('slots', 100))

        xheader = self._context.middleware_get_task_context()
        bufchan.emit(method, args, xheader)

        try:
            if kargs.get('async', False) is False:
                return self._process_response(method, bufchan, timeout)

            async_result = gevent.event.AsyncResult()
            gevent.spawn(self._process_response, method, bufchan,
                    timeout).link(async_result)
            return async_result
        except:
            bufchan.close()
            bufchan.channel.close()
            bufchan.channel.channel.close()
            raise

    def __getattr__(self, method):
        return lambda *args, **kargs: self(method, *args, **kargs)


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

    def process_call(self, context, bufchan, event, functor):
        result = context.middleware_call_procedure(functor, *event.args)
        bufchan.emit('OK', (result,), context.middleware_get_task_context())

    def accept_answer(self, event):
        return True

    def process_answer(self, context, bufchan, event, method, timeout,
            raise_remote_error):
        result = event.args[0]
        if event.name == 'ERR':
            raise_remote_error(event)
        bufchan.close()
        bufchan.channel.close()
        bufchan.channel.channel.close()
        return result


class rep(DecoratorBase):
    pattern = PatternReqRep()


class PatternReqStream():

    def process_call(self, context, bufchan, event, functor):
        xheader = context.middleware_get_task_context()
        for result in iter(context.middleware_call_procedure(functor,
                *event.args)):
            bufchan.emit('STREAM', result, xheader)
        bufchan.emit('STREAM_DONE', None, xheader)

    def accept_answer(self, event):
        return event.name in ('STREAM', 'STREAM_DONE')

    def process_answer(self, context, bufchan, event, method, timeout,
            raise_remote_error):
        def iterator(event):
            while event.name == 'STREAM':
                yield event.args
                event = bufchan.recv()
            if event.name == 'ERR':
                raise_remote_error(event)
            bufchan.close()
            bufchan.channel.channel.close()
        return iterator(event)


class stream(DecoratorBase):
    pattern = PatternReqStream()


class Server(SocketBase, ServerBase):

    def __init__(self, methods=None, name=None, context=None, pool_size=None,
            heartbeat=5):
        SocketBase.__init__(self, zmq.XREP, context)
        if methods is None:
            methods = self
        methods = ServerBase._zerorpc_filter_methods(Server, self, methods)
        ServerBase.__init__(self, self._events, methods, name, context,
                pool_size, heartbeat)

    def close(self):
        ServerBase.close(self)
        SocketBase.close(self)


class Client(SocketBase, ClientBase):
    patterns = [PatternReqStream(), PatternReqRep()]

    def __init__(self, connect_to=None, context=None, timeout=30, heartbeat=5,
            passive_heartbeat=False):
        SocketBase.__init__(self, zmq.XREQ, context=context)
        ClientBase.__init__(self, self._events, Client.patterns, context,
                timeout, heartbeat, passive_heartbeat)
        if connect_to:
            self.connect(connect_to)

    def close(self):
        ClientBase.close(self)
        SocketBase.close(self)


class Pusher(SocketBase):

    def __init__(self, context=None, zmq_socket=zmq.PUSH):
        super(Pusher, self).__init__(zmq_socket, context=context)

    def __call__(self, method, *args):
        self._events.emit(method, args,
                self._context.middleware_get_task_context())

    def __getattr__(self, method):
        return lambda *args: self(method, *args)


class Puller(SocketBase):

    def __init__(self, methods=None, context=None, zmq_socket=zmq.PULL):
        super(Puller, self).__init__(zmq_socket, context=context)

        if methods is None:
            methods = self

        self._methods = ServerBase._zerorpc_filter_methods(Puller, self, methods)
        self._receiver_task = None

    def close(self):
        self.stop()
        super(Puller, self).close()

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
                self._context.middleware_load_task_context(event.header)
                self._context.middleware_call_procedure(
                    self._methods[event.name],
                    *event.args)
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

    def __init__(self, methods=None, context=None):
        super(Subscriber, self).__init__(methods=methods, context=context,
                zmq_socket=zmq.SUB)
        self._events.setsockopt(zmq.SUBSCRIBE, '')


def fork_task_context(functor, context=None):
    '''Wrap a functor to transfer context.

        Usage example:
            gevent.spawn(zerorpc.fork_task_context(myfunction), args...)

        The goal is to permit context "inheritance" from a task to another.
        Consider the following example:

            zerorpc.Server receive a new event
              - task1 is created to handle this event this task will be linked
                to the initial event context. zerorpc.Server does that for you.
              - task1 make use of some zerorpc.Client instances, the initial
                event context is transfered on every call.

              - task1 spawn a new task2.
              - task2 make use of some zerorpc.Client instances, it's a fresh
                context. Thus there is no link to the initial context that
                spawned task1.

              - task1 spawn a new fork_task_context(task3).
              - task3 make use of some zerorpc.Client instances, the initial
                event context is transfered on every call.

        A real use case is a distributed tracer. Each time a new event is
        created, a trace_id is injected in it or copied from the current task
        context. This permit passing the trace_id from a zerorpc.Server to
        another via zerorpc.Client.

        The simple rule to know if a task need to be wrapped is:
            - if the new task will make any zerorpc call, it should be wrapped.
    '''
    context = context or Context.get_instance()
    header = context.middleware_get_task_context()
    def wrapped(*args, **kargs):
        context.middleware_load_task_context(header)
        return functor(*args, **kargs)
    return wrapped
