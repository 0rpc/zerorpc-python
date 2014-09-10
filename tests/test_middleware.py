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


from nose.tools import assert_raises
import gevent
import gevent.local
import random
import hashlib
import sys

from zerorpc import zmq
import zerorpc
from testutils import teardown, random_ipc_endpoint, TIME_FACTOR


def test_resolve_endpoint():
    test_endpoint = random_ipc_endpoint()
    c = zerorpc.Context()

    def resolve(endpoint):
        if endpoint == 'titi':
            return test_endpoint
        return endpoint

    cnt = c.register_middleware({
        'resolve_endpoint': resolve
        })
    print 'registered_count:', cnt
    assert cnt == 1

    print 'resolve titi:', c.hook_resolve_endpoint('titi')
    assert c.hook_resolve_endpoint('titi') == test_endpoint

    print 'resolve toto:', c.hook_resolve_endpoint('toto')
    assert c.hook_resolve_endpoint('toto') == 'toto'

    class Resolver():

        def resolve_endpoint(self, endpoint):
            if endpoint == 'toto':
                return test_endpoint
            return endpoint

    cnt = c.register_middleware(Resolver())
    print 'registered_count:', cnt
    assert cnt == 1

    print 'resolve titi:', c.hook_resolve_endpoint('titi')
    assert c.hook_resolve_endpoint('titi') == test_endpoint
    print 'resolve toto:', c.hook_resolve_endpoint('toto')
    assert c.hook_resolve_endpoint('toto') == test_endpoint

    c2 = zerorpc.Context()
    print 'resolve titi:', c2.hook_resolve_endpoint('titi')
    assert c2.hook_resolve_endpoint('titi') == 'titi'
    print 'resolve toto:', c2.hook_resolve_endpoint('toto')
    assert c2.hook_resolve_endpoint('toto') == 'toto'


def test_resolve_endpoint_events():
    test_endpoint = random_ipc_endpoint()
    c = zerorpc.Context()

    class Resolver():
        def resolve_endpoint(self, endpoint):
            if endpoint == 'some_service':
                return test_endpoint
            return endpoint

    class Srv(zerorpc.Server):
        def hello(self):
            print 'heee'
            return 'world'

    srv = Srv(heartbeat=TIME_FACTOR * 1, context=c)
    if sys.version_info < (2, 7):
        assert_raises(zmq.ZMQError, srv.bind, 'some_service')
    else:
        with assert_raises(zmq.ZMQError):
            srv.bind('some_service')

    cnt = c.register_middleware(Resolver())
    assert cnt == 1
    srv.bind('some_service')
    gevent.spawn(srv.run)

    client = zerorpc.Client(heartbeat=TIME_FACTOR * 1, context=c)
    client.connect('some_service')
    assert client.hello() == 'world'

    client.close()
    srv.close()


class Tracer:
    '''Used by test_task_context_* tests'''
    def __init__(self, identity):
        self._identity = identity
        self._locals = gevent.local.local()
        self._log = []

    @property
    def trace_id(self):
        return self._locals.__dict__.get('trace_id', None)

    def load_task_context(self, event_header):
        self._locals.trace_id = event_header.get('trace_id', None)
        print self._identity, 'load_task_context', self.trace_id
        self._log.append(('load', self.trace_id))

    def get_task_context(self):
        if self.trace_id is None:
            # just an ugly code to generate a beautiful little hash.
            self._locals.trace_id = '<{0}>'.format(hashlib.md5(
                    str(random.random())[3:]
                    ).hexdigest()[0:6].upper())
            print self._identity, 'get_task_context! [make a new one]', self.trace_id
            self._log.append(('new', self.trace_id))
        else:
            print self._identity, 'get_task_context! [reuse]', self.trace_id
            self._log.append(('reuse', self.trace_id))
        return { 'trace_id': self.trace_id }


def test_task_context():
    endpoint = random_ipc_endpoint()
    srv_ctx = zerorpc.Context()
    cli_ctx = zerorpc.Context()

    srv_tracer = Tracer('[server]')
    srv_ctx.register_middleware(srv_tracer)
    cli_tracer = Tracer('[client]')
    cli_ctx.register_middleware(cli_tracer)

    class Srv:
        def echo(self, msg):
            return msg

        @zerorpc.stream
        def stream(self):
            yield 42

    srv = zerorpc.Server(Srv(), context=srv_ctx)
    srv.bind(endpoint)
    srv_task = gevent.spawn(srv.run)

    c = zerorpc.Client(context=cli_ctx)
    c.connect(endpoint)

    assert c.echo('hello') == 'hello'
    for x in c.stream():
        assert x == 42

    srv.stop()
    srv_task.join()

    assert cli_tracer._log == [
            ('new', cli_tracer.trace_id),
            ('reuse', cli_tracer.trace_id),
            ]
    assert srv_tracer._log == [
            ('load', cli_tracer.trace_id),
            ('reuse', cli_tracer.trace_id),
            ('load', cli_tracer.trace_id),
            ('reuse', cli_tracer.trace_id),
            ]

def test_task_context_relay():
    endpoint1 = random_ipc_endpoint()
    endpoint2 = random_ipc_endpoint()
    srv_ctx = zerorpc.Context()
    srv_relay_ctx = zerorpc.Context()
    cli_ctx = zerorpc.Context()

    srv_tracer = Tracer('[server]')
    srv_ctx.register_middleware(srv_tracer)
    srv_relay_tracer = Tracer('[server_relay]')
    srv_relay_ctx.register_middleware(srv_relay_tracer)
    cli_tracer = Tracer('[client]')
    cli_ctx.register_middleware(cli_tracer)

    class Srv:
        def echo(self, msg):
            return msg

    srv = zerorpc.Server(Srv(), context=srv_ctx)
    srv.bind(endpoint1)
    srv_task = gevent.spawn(srv.run)

    c_relay = zerorpc.Client(context=srv_relay_ctx)
    c_relay.connect(endpoint1)

    class SrvRelay:
        def echo(self, msg):
            return c_relay.echo('relay' + msg) + 'relayed'

    srv_relay = zerorpc.Server(SrvRelay(), context=srv_relay_ctx)
    srv_relay.bind(endpoint2)
    srv_relay_task = gevent.spawn(srv_relay.run)

    c = zerorpc.Client(context=cli_ctx)
    c.connect(endpoint2)

    assert c.echo('hello') == 'relayhellorelayed'

    srv_relay.stop()
    srv.stop()
    srv_relay_task.join()
    srv_task.join()

    assert cli_tracer._log == [
            ('new', cli_tracer.trace_id),
            ]
    assert srv_relay_tracer._log == [
            ('load', cli_tracer.trace_id),
            ('reuse', cli_tracer.trace_id),
            ('reuse', cli_tracer.trace_id),
            ]
    assert srv_tracer._log == [
            ('load', cli_tracer.trace_id),
            ('reuse', cli_tracer.trace_id),
            ]

def test_task_context_relay_fork():
    endpoint1 = random_ipc_endpoint()
    endpoint2 = random_ipc_endpoint()
    srv_ctx = zerorpc.Context()
    srv_relay_ctx = zerorpc.Context()
    cli_ctx = zerorpc.Context()

    srv_tracer = Tracer('[server]')
    srv_ctx.register_middleware(srv_tracer)
    srv_relay_tracer = Tracer('[server_relay]')
    srv_relay_ctx.register_middleware(srv_relay_tracer)
    cli_tracer = Tracer('[client]')
    cli_ctx.register_middleware(cli_tracer)

    class Srv:
        def echo(self, msg):
            return msg

    srv = zerorpc.Server(Srv(), context=srv_ctx)
    srv.bind(endpoint1)
    srv_task = gevent.spawn(srv.run)

    c_relay = zerorpc.Client(context=srv_relay_ctx)
    c_relay.connect(endpoint1)

    class SrvRelay:
        def echo(self, msg):
            def dothework(msg):
                return c_relay.echo(msg) + 'relayed'
            g = gevent.spawn(zerorpc.fork_task_context(dothework,
                srv_relay_ctx), 'relay' + msg)
            print 'relaying in separate task:', g
            r = g.get()
            print 'back to main task'
            return r

    srv_relay = zerorpc.Server(SrvRelay(), context=srv_relay_ctx)
    srv_relay.bind(endpoint2)
    srv_relay_task = gevent.spawn(srv_relay.run)

    c = zerorpc.Client(context=cli_ctx)
    c.connect(endpoint2)

    assert c.echo('hello') == 'relayhellorelayed'

    srv_relay.stop()
    srv.stop()
    srv_relay_task.join()
    srv_task.join()

    assert cli_tracer._log == [
            ('new', cli_tracer.trace_id),
            ]
    assert srv_relay_tracer._log == [
            ('load', cli_tracer.trace_id),
            ('reuse', cli_tracer.trace_id),
            ('load', cli_tracer.trace_id),
            ('reuse', cli_tracer.trace_id),
            ('reuse', cli_tracer.trace_id),
            ]
    assert srv_tracer._log == [
            ('load', cli_tracer.trace_id),
            ('reuse', cli_tracer.trace_id),
            ]


def test_task_context_pushpull():
    endpoint = random_ipc_endpoint()
    puller_ctx = zerorpc.Context()
    pusher_ctx = zerorpc.Context()

    puller_tracer = Tracer('[puller]')
    puller_ctx.register_middleware(puller_tracer)
    pusher_tracer = Tracer('[pusher]')
    pusher_ctx.register_middleware(pusher_tracer)

    trigger = gevent.event.Event()

    class Puller:
        def echo(self, msg):
            trigger.set()

    puller = zerorpc.Puller(Puller(), context=puller_ctx)
    puller.bind(endpoint)
    puller_task = gevent.spawn(puller.run)

    c = zerorpc.Pusher(context=pusher_ctx)
    c.connect(endpoint)

    trigger.clear()
    c.echo('hello')
    trigger.wait()

    puller.stop()
    puller_task.join()

    assert pusher_tracer._log == [
            ('new', pusher_tracer.trace_id),
            ]
    assert puller_tracer._log == [
            ('load', pusher_tracer.trace_id),
            ]


def test_task_context_pubsub():
    endpoint = random_ipc_endpoint()
    subscriber_ctx = zerorpc.Context()
    publisher_ctx = zerorpc.Context()

    subscriber_tracer = Tracer('[subscriber]')
    subscriber_ctx.register_middleware(subscriber_tracer)
    publisher_tracer = Tracer('[publisher]')
    publisher_ctx.register_middleware(publisher_tracer)

    trigger = gevent.event.Event()

    class Subscriber:
        def echo(self, msg):
            trigger.set()

    subscriber = zerorpc.Subscriber(Subscriber(), context=subscriber_ctx)
    subscriber.bind(endpoint)
    subscriber_task = gevent.spawn(subscriber.run)

    c = zerorpc.Publisher(context=publisher_ctx)
    c.connect(endpoint)

    trigger.clear()
    # We need this retry logic to wait that the subscriber.run coroutine starts
    # reading (the published messages will go to /dev/null until then).
    while not trigger.is_set():
        c.echo('pub...')
        if trigger.wait(TIME_FACTOR * 1):
            break

    subscriber.stop()
    subscriber_task.join()

    print publisher_tracer._log
    assert ('new', publisher_tracer.trace_id) in publisher_tracer._log
    print subscriber_tracer._log
    assert ('load', publisher_tracer.trace_id) in subscriber_tracer._log


class InspectExceptionMiddleware(Tracer):
    def __init__(self, barrier=None):
        self.called = False
        self._barrier = barrier
        Tracer.__init__(self, identity='[server]')

    def server_inspect_exception(self, request_event, reply_event, task_context, exc_info):
        assert 'trace_id' in task_context
        assert request_event.name == 'echo'
        if self._barrier: # Push/Pull
            assert reply_event is None
        else: # Req/Rep or Req/Stream
            assert reply_event.name == 'ERR'
        exc_type, exc_value, exc_traceback = exc_info
        self.called = True
        if self._barrier:
            self._barrier.set()

class Srv(object):

    def echo(self, msg):
        raise RuntimeError(msg)

    @zerorpc.stream
    def echoes(self, msg):
        raise RuntimeError(msg)

def test_server_inspect_exception_middleware():
    endpoint = random_ipc_endpoint()

    middleware = InspectExceptionMiddleware()
    ctx = zerorpc.Context()
    ctx.register_middleware(middleware)

    module = Srv()
    server = zerorpc.Server(module, context=ctx)
    server.bind(endpoint)
    gevent.spawn(server.run)

    client = zerorpc.Client()
    client.connect(endpoint)

    try:
        client.echo('This is a test which should call the InspectExceptionMiddleware')
    except zerorpc.exceptions.RemoteError as ex:
        assert ex.name == 'RuntimeError'

    client.close()
    server.close()

    assert middleware.called is True

def test_server_inspect_exception_middleware_puller():
    endpoint = random_ipc_endpoint()

    barrier = gevent.event.Event()
    middleware = InspectExceptionMiddleware(barrier)
    ctx = zerorpc.Context()
    ctx.register_middleware(middleware)

    module = Srv()
    server = zerorpc.Puller(module, context=ctx)
    server.bind(endpoint)
    gevent.spawn(server.run)

    client = zerorpc.Pusher()
    client.connect(endpoint)

    barrier.clear()
    client.echo('This is a test which should call the InspectExceptionMiddleware')
    barrier.wait(timeout=TIME_FACTOR * 2)

    client.close()
    server.close()

    assert middleware.called is True

def test_server_inspect_exception_middleware_stream():
    endpoint = random_ipc_endpoint()

    middleware = InspectExceptionMiddleware()
    ctx = zerorpc.Context()
    ctx.register_middleware(middleware)

    module = Srv()
    server = zerorpc.Server(module, context=ctx)
    server.bind(endpoint)
    gevent.spawn(server.run)

    client = zerorpc.Client()
    client.connect(endpoint)

    try:
        client.echo('This is a test which should call the InspectExceptionMiddleware')
    except zerorpc.exceptions.RemoteError as ex:
        assert ex.name == 'RuntimeError'

    client.close()
    server.close()

    assert middleware.called is True
