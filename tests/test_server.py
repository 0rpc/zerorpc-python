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
import sys

from zerorpc import zmq
import zerorpc
from testutils import teardown, random_ipc_endpoint


def test_server_manual():
    endpoint = random_ipc_endpoint()

    class MySrv(zerorpc.Server):

        def lolita(self):
            return 42

        def add(self, a, b):
            return a + b

    srv = MySrv()
    srv.bind(endpoint)
    gevent.spawn(srv.run)

    client_events = zerorpc.Events(zmq.DEALER)
    client_events.connect(endpoint)
    client = zerorpc.ChannelMultiplexer(client_events, ignore_broadcast=True)

    client_channel = client.channel()
    client_channel.emit('lolita', tuple())
    event = client_channel.recv()
    assert list(event.args) == [42]
    client_channel.close()

    client_channel = client.channel()
    client_channel.emit('add', (1, 2))
    event = client_channel.recv()
    assert list(event.args) == [3]
    client_channel.close()
    srv.stop()


def test_client_server():
    endpoint = random_ipc_endpoint()

    class MySrv(zerorpc.Server):

        def lolita(self):
            return 42

        def add(self, a, b):
            return a + b

    srv = MySrv()
    srv.bind(endpoint)
    gevent.spawn(srv.run)

    client = zerorpc.Client()
    client.connect(endpoint)

    print client.lolita()
    assert client.lolita() == 42

    print client.add(1, 4)
    assert client.add(1, 4) == 5

def test_wrapped_client_server():
    endpoint = random_ipc_endpoint()
    
    class MySrv(object):
        def lolita(self):
            return 42

        def add(self, a, b):
            return a + b
        
        def run(self):
            return "for the hills"
        

    srv = zerorpc.Server(MySrv())
    srv.bind(endpoint)
    gevent.spawn(srv.run)

    client = zerorpc.Client()
    client.connect(endpoint)

    print client.lolita()
    assert client.lolita() == 42

    print client.add(1, 4)
    assert client.add(1, 4) == 5

    print client.run() == "for the hills"
    assert client.run() == "for the hills"

def test_exposing_list_dict():
    endpoint = random_ipc_endpoint()
    l = [0,2,2,3]
    d = {"one": 1, "two": 2}

    try:  
        server = zerorpc.Server(l)
        server.bind(endpoint)
        thread = gevent.spawn(server.run)
    except Exception, e:
        raise AssertionError(e), None, sys.exc_info()[2]

    client = zerorpc.Client()
    client.connect(endpoint)
    
    assert client.count(2) == 2
    
    server.stop()
    server.close()
    thread.kill()
    client.close()
    
    try:
        server = zerorpc.Server(d)
        server.bind(endpoint)
        gevent.spawn(server.run)
    except Exception, e:
        raise AssertionError(e), None, sys.exc_info()[2]

    client = zerorpc.Client()
    client.connect(endpoint)

    print str(client.keys())
    assert "one" in client.keys()
    assert "two" in client.keys()
    assert "infinity" not in client.keys()
    
    server.stop()
    server.close()
    thread.kill()    
    client.close()
    
def test_client_server_client_timeout():
    endpoint = random_ipc_endpoint()

    class MySrv(zerorpc.Server):

        def lolita(self):
            return 42

        def add(self, a, b):
            gevent.sleep(10)
            return a + b

    srv = MySrv()
    srv.bind(endpoint)
    gevent.spawn(srv.run)

    client = zerorpc.Client(timeout=2)
    client.connect(endpoint)

    if sys.version_info < (2, 7):
        assert_raises(zerorpc.TimeoutExpired, client.add, 1, 4)
    else:
        with assert_raises(zerorpc.TimeoutExpired):
            print client.add(1, 4)
    client.close()
    srv.close()


def test_client_server_exception():
    endpoint = random_ipc_endpoint()

    class MySrv(zerorpc.Server):

        def raise_something(self, a):
            return a[4]

    srv = MySrv()
    srv.bind(endpoint)
    gevent.spawn(srv.run)

    client = zerorpc.Client(timeout=2)
    client.connect(endpoint)

    if sys.version_info < (2, 7):
        def _do_with_assert_raises():
            print client.raise_something(42)
        assert_raises(zerorpc.RemoteError, _do_with_assert_raises)
    else:
        with assert_raises(zerorpc.RemoteError):
            print client.raise_something(42)
    assert client.raise_something(range(5)) == 4
    client.close()
    srv.close()


def test_client_server_detailed_exception():
    endpoint = random_ipc_endpoint()

    class MySrv(zerorpc.Server):

        def raise_error(self):
            raise RuntimeError('oops!')

    srv = MySrv()
    srv.bind(endpoint)
    gevent.spawn(srv.run)

    client = zerorpc.Client(timeout=2)
    client.connect(endpoint)

    if sys.version_info < (2, 7):
        def _do_with_assert_raises():
            print client.raise_error()
        assert_raises(zerorpc.RemoteError, _do_with_assert_raises)
    else:
        with assert_raises(zerorpc.RemoteError):
            print client.raise_error()
    try:
        client.raise_error()
    except zerorpc.RemoteError as e:
        print 'got that:', e
        print 'name', e.name
        print 'msg', e.msg
        assert e.name == 'RuntimeError'
        assert e.msg == 'oops!'

    client.close()
    srv.close()


def test_exception_compat_v1():
    endpoint = random_ipc_endpoint()

    class MySrv(zerorpc.Server):
        pass

    srv = MySrv()
    srv.bind(endpoint)
    gevent.spawn(srv.run)

    client_events = zerorpc.Events(zmq.DEALER)
    client_events.connect(endpoint)
    client = zerorpc.ChannelMultiplexer(client_events, ignore_broadcast=True)

    rpccall = client.channel()
    rpccall.emit('donotexist', tuple())
    event = rpccall.recv()
    print event
    assert event.name == 'ERR'
    (name, msg, tb) = event.args
    print 'detailed error', name, msg, tb
    assert name == 'NameError'
    assert msg == 'donotexist'

    rpccall = client.channel()
    rpccall.emit('donotexist', tuple(), xheader=dict(v=1))
    event = rpccall.recv()
    print event
    assert event.name == 'ERR'
    (msg,) = event.args
    print 'msg only', msg
    assert msg == "NameError('donotexist',)"

    client_events.close()
    srv.close()


def test_removed_unscriptable_error_format_args_spec():

    class MySrv(zerorpc.Server):
        pass

    srv = MySrv()
    return_value = srv._format_args_spec(None)
    assert return_value is None
