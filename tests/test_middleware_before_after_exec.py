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

from __future__ import absolute_import
from builtins import range

import gevent
import zerorpc

from .testutils import teardown, random_ipc_endpoint, TIME_FACTOR

class EchoModule(object):

    def __init__(self, trigger=None):
        self.last_msg = None
        self._trigger = trigger

    def echo(self, msg):
        self.last_msg = 'echo: ' + msg
        if self._trigger:
            self._trigger.set()
        return self.last_msg

    @zerorpc.stream
    def echoes(self, msg):
        self.last_msg = 'echo: ' + msg
        for i in range(0, 3):
            yield self.last_msg

class ServerBeforeExecMiddleware(object):

    def __init__(self):
        self.called = False

    def server_before_exec(self, request_event):
        assert request_event.name == "echo" or request_event.name == "echoes"
        self.called = True

def test_hook_server_before_exec():
    zero_ctx = zerorpc.Context()
    endpoint = random_ipc_endpoint()

    test_server = zerorpc.Server(EchoModule(), context=zero_ctx)
    test_server.bind(endpoint)
    test_server_task = gevent.spawn(test_server.run)
    test_client = zerorpc.Client()
    test_client.connect(endpoint)

    # Test without a middleware
    assert test_client.echo("test") == "echo: test"

    # Test with a middleware
    test_middleware = ServerBeforeExecMiddleware()
    zero_ctx.register_middleware(test_middleware)
    assert test_middleware.called == False
    assert test_client.echo("test") == "echo: test"
    assert test_middleware.called == True

    test_server.stop()
    test_server_task.join()

def test_hook_server_before_exec_puller():
    zero_ctx = zerorpc.Context()
    trigger = gevent.event.Event()
    endpoint = random_ipc_endpoint()

    echo_module = EchoModule(trigger)
    test_server = zerorpc.Puller(echo_module, context=zero_ctx)
    test_server.bind(endpoint)
    test_server_task = gevent.spawn(test_server.run)
    test_client = zerorpc.Pusher()
    test_client.connect(endpoint)

    # Test without a middleware
    test_client.echo("test")
    trigger.wait(timeout=TIME_FACTOR * 2)
    assert echo_module.last_msg == "echo: test"
    trigger.clear()

    # Test with a middleware
    test_middleware = ServerBeforeExecMiddleware()
    zero_ctx.register_middleware(test_middleware)
    assert test_middleware.called == False
    test_client.echo("test with a middleware")
    trigger.wait(timeout=TIME_FACTOR * 2)
    assert echo_module.last_msg == "echo: test with a middleware"
    assert test_middleware.called == True

    test_server.stop()
    test_server_task.join()

def test_hook_server_before_exec_stream():
    zero_ctx = zerorpc.Context()
    endpoint = random_ipc_endpoint()

    test_server = zerorpc.Server(EchoModule(), context=zero_ctx)
    test_server.bind(endpoint)
    test_server_task = gevent.spawn(test_server.run)
    test_client = zerorpc.Client()
    test_client.connect(endpoint)

    # Test without a middleware
    for echo in test_client.echoes("test"):
        assert echo == "echo: test"

    # Test with a middleware
    test_middleware = ServerBeforeExecMiddleware()
    zero_ctx.register_middleware(test_middleware)
    assert test_middleware.called == False
    it = test_client.echoes("test")
    assert test_middleware.called == True
    assert next(it) == "echo: test"
    for echo in it:
        assert echo == "echo: test"

    test_server.stop()
    test_server_task.join()

class ServerAfterExecMiddleware(object):

    def __init__(self):
        self.called = False

    def server_after_exec(self, request_event, reply_event):
        self.called = True
        self.request_event_name = getattr(request_event, 'name', None)
        self.reply_event_name = getattr(reply_event, 'name', None)

def test_hook_server_after_exec():
    zero_ctx = zerorpc.Context()
    endpoint = random_ipc_endpoint()

    test_server = zerorpc.Server(EchoModule(), context=zero_ctx)
    test_server.bind(endpoint)
    test_server_task = gevent.spawn(test_server.run)
    test_client = zerorpc.Client()
    test_client.connect(endpoint)

    # Test without a middleware
    assert test_client.echo("test") == "echo: test"

    # Test with a middleware
    test_middleware = ServerAfterExecMiddleware()
    zero_ctx.register_middleware(test_middleware)
    assert test_middleware.called == False
    assert test_client.echo("test") == "echo: test"
    assert test_middleware.called == True
    assert test_middleware.request_event_name == 'echo'
    assert test_middleware.reply_event_name == 'OK'

    test_server.stop()
    test_server_task.join()

def test_hook_server_after_exec_puller():
    zero_ctx = zerorpc.Context()
    trigger = gevent.event.Event()
    endpoint = random_ipc_endpoint()

    echo_module = EchoModule(trigger)
    test_server = zerorpc.Puller(echo_module, context=zero_ctx)
    test_server.bind(endpoint)
    test_server_task = gevent.spawn(test_server.run)
    test_client = zerorpc.Pusher()
    test_client.connect(endpoint)

    # Test without a middleware
    test_client.echo("test")
    trigger.wait(timeout=TIME_FACTOR * 2)
    assert echo_module.last_msg == "echo: test"
    trigger.clear()

    # Test with a middleware
    test_middleware = ServerAfterExecMiddleware()
    zero_ctx.register_middleware(test_middleware)
    assert test_middleware.called == False
    test_client.echo("test with a middleware")
    trigger.wait(timeout=TIME_FACTOR * 2)
    assert echo_module.last_msg == "echo: test with a middleware"
    assert test_middleware.called == True
    assert test_middleware.request_event_name == 'echo'
    assert test_middleware.reply_event_name is None

    test_server.stop()
    test_server_task.join()

def test_hook_server_after_exec_stream():
    zero_ctx = zerorpc.Context()
    endpoint = random_ipc_endpoint()

    test_server = zerorpc.Server(EchoModule(), context=zero_ctx)
    test_server.bind(endpoint)
    test_server_task = gevent.spawn(test_server.run)
    test_client = zerorpc.Client()
    test_client.connect(endpoint)

    # Test without a middleware
    for echo in test_client.echoes("test"):
        assert echo == "echo: test"

    # Test with a middleware
    test_middleware = ServerAfterExecMiddleware()
    zero_ctx.register_middleware(test_middleware)
    assert test_middleware.called == False
    it = test_client.echoes("test")
    assert next(it) == "echo: test"
    assert test_middleware.called == False
    for echo in it:
        assert echo == "echo: test"
    assert test_middleware.called == True
    assert test_middleware.request_event_name == 'echoes'
    assert test_middleware.reply_event_name == 'STREAM_DONE'

    test_server.stop()
    test_server_task.join()

class BrokenEchoModule(object):

    def __init__(self, trigger=None):
        self.last_msg = None
        self._trigger = trigger

    def echo(self, msg):
        try:
            self.last_msg = "Raise"
            raise RuntimeError("BrokenEchoModule")
        finally:
            if self._trigger:
                self._trigger.set()

    @zerorpc.stream
    def echoes(self, msg):
        self.echo(msg)

def test_hook_server_after_exec_on_error():
    zero_ctx = zerorpc.Context()
    endpoint = random_ipc_endpoint()

    test_server = zerorpc.Server(BrokenEchoModule(), context=zero_ctx)
    test_server.bind(endpoint)
    test_server_task = gevent.spawn(test_server.run)
    test_client = zerorpc.Client()
    test_client.connect(endpoint)

    test_middleware = ServerAfterExecMiddleware()
    zero_ctx.register_middleware(test_middleware)
    assert test_middleware.called == False
    try:
        test_client.echo("test")
    except zerorpc.RemoteError:
        pass
    assert test_middleware.called == False

    test_server.stop()
    test_server_task.join()

def test_hook_server_after_exec_on_error_puller():
    zero_ctx = zerorpc.Context()
    trigger = gevent.event.Event()
    endpoint = random_ipc_endpoint()

    echo_module = BrokenEchoModule(trigger)
    test_server = zerorpc.Puller(echo_module, context=zero_ctx)
    test_server.bind(endpoint)
    test_server_task = gevent.spawn(test_server.run)
    test_client = zerorpc.Pusher()
    test_client.connect(endpoint)

    test_middleware = ServerAfterExecMiddleware()
    zero_ctx.register_middleware(test_middleware)
    assert test_middleware.called == False
    try:
        test_client.echo("test with a middleware")
        trigger.wait(timeout=TIME_FACTOR * 2)
    except zerorpc.RemoteError:
        pass
    assert echo_module.last_msg == "Raise"
    assert test_middleware.called == False

    test_server.stop()
    test_server_task.join()

def test_hook_server_after_exec_on_error_stream():
    zero_ctx = zerorpc.Context()
    endpoint = random_ipc_endpoint()

    test_server = zerorpc.Server(BrokenEchoModule(), context=zero_ctx)
    test_server.bind(endpoint)
    test_server_task = gevent.spawn(test_server.run)
    test_client = zerorpc.Client()
    test_client.connect(endpoint)

    test_middleware = ServerAfterExecMiddleware()
    zero_ctx.register_middleware(test_middleware)
    assert test_middleware.called == False
    try:
        test_client.echoes("test")
    except zerorpc.RemoteError:
        pass
    assert test_middleware.called == False

    test_server.stop()
    test_server_task.join()
