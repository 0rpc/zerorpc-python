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

import gevent
import zerorpc

from testutils import random_ipc_endpoint

class EchoModule(object):

    def __init__(self, trigger=None):
        self.last_msg = None
        self._trigger = trigger

    def echo(self, msg):
        self.last_msg = "echo: " + msg
        if self._trigger:
            self._trigger.set()
        return self.last_msg

    @zerorpc.stream
    def echoes(self, msg):
        self.last_msg = "echo: " + msg
        for i in xrange(0, 3):
            yield self.last_msg

    def crash(self, msg):
        try:
            self.last_msg = "raise: " + msg
            raise RuntimeError("BrokenEchoModule")
        finally:
            if self._trigger:
                self._trigger.set()

    @zerorpc.stream
    def echoes_crash(self, msg):
        self.crash(msg)

    def timeout(self, msg):
        self.last_msg = "timeout: " + msg
        gevent.sleep(2)

def test_hook_client_before_request():

    class ClientBeforeRequestMiddleware(object):
        def __init__(self):
            self.called = False
        def client_before_request(self, event):
            self.called = True
            self.method = event.name

    zero_ctx = zerorpc.Context()
    endpoint = random_ipc_endpoint()

    test_server = zerorpc.Server(EchoModule(), context=zero_ctx)
    test_server.bind(endpoint)
    test_server_task = gevent.spawn(test_server.run)

    test_client = zerorpc.Client(context=zero_ctx)
    test_client.connect(endpoint)

    assert test_client.echo("test") == "echo: test"

    test_middleware = ClientBeforeRequestMiddleware()
    zero_ctx.register_middleware(test_middleware)
    assert test_middleware.called == False
    assert test_client.echo("test") == "echo: test"
    assert test_middleware.called == True
    assert test_middleware.method == 'echo'

    test_server.stop()
    test_server_task.join()

class ClientAfterRequestMiddleware(object):
    def __init__(self):
        self.called = False
    def client_after_request(self, req_event, rep_event, exception):
        self.called = True
        assert req_event is not None
        assert req_event.name == "echo" or req_event.name == "echoes"
        self.retcode = rep_event.name
        assert exception is None

def test_hook_client_after_request():
    zero_ctx = zerorpc.Context()
    endpoint = random_ipc_endpoint()

    test_server = zerorpc.Server(EchoModule(), context=zero_ctx)
    test_server.bind(endpoint)
    test_server_task = gevent.spawn(test_server.run)

    test_client = zerorpc.Client(context=zero_ctx)
    test_client.connect(endpoint)

    assert test_client.echo("test") == "echo: test"

    test_middleware = ClientAfterRequestMiddleware()
    zero_ctx.register_middleware(test_middleware)
    assert test_middleware.called == False
    assert test_client.echo("test") == "echo: test"
    assert test_middleware.called == True
    assert test_middleware.retcode == 'OK'

    test_server.stop()
    test_server_task.join()

def test_hook_client_after_request_stream():
    zero_ctx = zerorpc.Context()
    endpoint = random_ipc_endpoint()

    test_server = zerorpc.Server(EchoModule(), context=zero_ctx)
    test_server.bind(endpoint)
    test_server_task = gevent.spawn(test_server.run)

    test_client = zerorpc.Client(context=zero_ctx)
    test_client.connect(endpoint)

    it = test_client.echoes("test")
    assert next(it) == "echo: test"
    for echo in it:
        assert echo == "echo: test"

    test_middleware = ClientAfterRequestMiddleware()
    zero_ctx.register_middleware(test_middleware)
    assert test_middleware.called == False
    it = test_client.echoes("test")
    assert next(it) == "echo: test"
    assert test_middleware.called == False
    for echo in it:
        assert echo == "echo: test"
    assert test_middleware.called == True
    assert test_middleware.retcode == 'STREAM_DONE'

    test_server.stop()
    test_server_task.join()

def test_hook_client_after_request_timeout():

    class ClientAfterRequestMiddleware(object):
        def __init__(self):
            self.called = False
        def client_after_request(self, req_event, rep_event, exception):
            self.called = True
            assert req_event is not None
            assert req_event.name == "timeout"
            assert rep_event is None

    zero_ctx = zerorpc.Context()
    test_middleware = ClientAfterRequestMiddleware()
    zero_ctx.register_middleware(test_middleware)
    endpoint = random_ipc_endpoint()

    test_server = zerorpc.Server(EchoModule(), context=zero_ctx)
    test_server.bind(endpoint)
    test_server_task = gevent.spawn(test_server.run)

    test_client = zerorpc.Client(timeout=1, context=zero_ctx)
    test_client.connect(endpoint)

    assert test_middleware.called == False
    try:
        test_client.timeout("test")
    except zerorpc.TimeoutExpired as ex:
        assert test_middleware.called == True
        assert "timeout" in ex.args[0]

    test_server.stop()
    test_server_task.join()

class ClientAfterFailedRequestMiddleware(object):
    def __init__(self):
        self.called = False
    def client_after_request(self, req_event, rep_event, exception):
        assert req_event is not None
        assert req_event.name == "crash" or req_event.name == "echoes_crash"
        self.called = True
        assert isinstance(exception, zerorpc.RemoteError)
        assert exception.name == 'RuntimeError'
        assert 'BrokenEchoModule' in exception.msg
        assert rep_event.name == 'ERR'

def test_hook_client_after_request_remote_error():

    zero_ctx = zerorpc.Context()
    test_middleware = ClientAfterFailedRequestMiddleware()
    zero_ctx.register_middleware(test_middleware)
    endpoint = random_ipc_endpoint()

    test_server = zerorpc.Server(EchoModule(), context=zero_ctx)
    test_server.bind(endpoint)
    test_server_task = gevent.spawn(test_server.run)

    test_client = zerorpc.Client(timeout=1, context=zero_ctx)
    test_client.connect(endpoint)

    assert test_middleware.called == False
    try:
        test_client.crash("test")
    except zerorpc.RemoteError:
        assert test_middleware.called == True

    test_server.stop()
    test_server_task.join()

def test_hook_client_after_request_remote_error_stream():

    zero_ctx = zerorpc.Context()
    test_middleware = ClientAfterFailedRequestMiddleware()
    zero_ctx.register_middleware(test_middleware)
    endpoint = random_ipc_endpoint()

    test_server = zerorpc.Server(EchoModule(), context=zero_ctx)
    test_server.bind(endpoint)
    test_server_task = gevent.spawn(test_server.run)

    test_client = zerorpc.Client(timeout=1, context=zero_ctx)
    test_client.connect(endpoint)

    assert test_middleware.called == False
    try:
        test_client.echoes_crash("test")
    except zerorpc.RemoteError:
        assert test_middleware.called == True

    test_server.stop()
    test_server_task.join()

def test_hook_client_handle_remote_error_inspect():

    class ClientHandleRemoteErrorMiddleware(object):
        def __init__(self):
            self.called = False
        def client_handle_remote_error(self, event):
            self.called = True

    test_middleware = ClientHandleRemoteErrorMiddleware()
    zero_ctx = zerorpc.Context()
    zero_ctx.register_middleware(test_middleware)
    endpoint = random_ipc_endpoint()

    test_server = zerorpc.Server(EchoModule(), context=zero_ctx)
    test_server.bind(endpoint)
    test_server_task = gevent.spawn(test_server.run)

    test_client = zerorpc.Client(context=zero_ctx)
    test_client.connect(endpoint)

    assert test_middleware.called == False
    try:
        test_client.crash("test")
    except zerorpc.RemoteError as ex:
        assert test_middleware.called == True
        assert ex.name == "RuntimeError"

    test_server.stop()
    test_server_task.join()

# This is a seriously broken idea, but possible nonetheless
class ClientEvalRemoteErrorMiddleware(object):
    def __init__(self):
        self.called = False
    def client_handle_remote_error(self, event):
        self.called = True
        name, msg, tb = event.args
        etype = eval(name)
        e = etype(tb)
        return e

def test_hook_client_handle_remote_error_eval():
    test_middleware = ClientEvalRemoteErrorMiddleware()
    zero_ctx = zerorpc.Context()
    zero_ctx.register_middleware(test_middleware)
    endpoint = random_ipc_endpoint()

    test_server = zerorpc.Server(EchoModule(), context=zero_ctx)
    test_server.bind(endpoint)
    test_server_task = gevent.spawn(test_server.run)

    test_client = zerorpc.Client(context=zero_ctx)
    test_client.connect(endpoint)

    assert test_middleware.called == False
    try:
        test_client.crash("test")
    except RuntimeError as ex:
        assert test_middleware.called == True
        assert "BrokenEchoModule" in ex.args[0]

    test_server.stop()
    test_server_task.join()

def test_hook_client_handle_remote_error_eval_stream():
    test_middleware = ClientEvalRemoteErrorMiddleware()
    zero_ctx = zerorpc.Context()
    zero_ctx.register_middleware(test_middleware)
    endpoint = random_ipc_endpoint()

    test_server = zerorpc.Server(EchoModule(), context=zero_ctx)
    test_server.bind(endpoint)
    test_server_task = gevent.spawn(test_server.run)

    test_client = zerorpc.Client(context=zero_ctx)
    test_client.connect(endpoint)

    assert test_middleware.called == False
    try:
        test_client.echoes_crash("test")
    except RuntimeError as ex:
        assert test_middleware.called == True
        assert "BrokenEchoModule" in ex.args[0]

    test_server.stop()
    test_server_task.join()

def test_hook_client_after_request_custom_error():

    # This is a seriously broken idea, but possible nonetheless
    class ClientEvalInspectRemoteErrorMiddleware(object):
        def __init__(self):
            self.called = False
        def client_handle_remote_error(self, event):
            name, msg, tb = event.args
            etype = eval(name)
            e = etype(tb)
            return e
        def client_after_request(self, req_event, rep_event, exception):
            assert req_event is not None
            assert req_event.name == "crash"
            self.called = True
            assert isinstance(exception, RuntimeError)

    test_middleware = ClientEvalInspectRemoteErrorMiddleware()
    zero_ctx = zerorpc.Context()
    zero_ctx.register_middleware(test_middleware)
    endpoint = random_ipc_endpoint()

    test_server = zerorpc.Server(EchoModule(), context=zero_ctx)
    test_server.bind(endpoint)
    test_server_task = gevent.spawn(test_server.run)

    test_client = zerorpc.Client(context=zero_ctx)
    test_client.connect(endpoint)

    assert test_middleware.called == False
    try:
        test_client.crash("test")
    except RuntimeError as ex:
        assert test_middleware.called == True
        assert "BrokenEchoModule" in ex.args[0]

    test_server.stop()
    test_server_task.join()
