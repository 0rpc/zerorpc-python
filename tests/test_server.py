# -*- coding: utf-8 -*-
# Open Source Initiative OSI - The MIT License (MIT):Licensing
#
# The MIT License (MIT)
# Copyright (c) 2012 DotCloud Inc (François-Xavier Bourlet <fx@dotcloud.com>)
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

from zerorpc import zmq
import zerorpc

def test_server_manual():
    endpoint = 'ipc://test_server_manual'

    class MySrv(zerorpc.Server):

        def lolita(self):
            return 42

        def add(self, a, b):
            return a + b

    srv = MySrv()
    srv.bind(endpoint)
    gevent.spawn(srv.run)

    client_events = zerorpc.Events(zmq.XREQ)
    client_events.connect(endpoint)
    client = zerorpc.ChannelMultiplexer(client_events, ignore_broadcast=True)

    client_channel = client.channel()
    client_channel.emit('lolita', tuple())
    event = client_channel.recv()
    assert event.args == (42,)
    client_channel.close()

    client_channel = client.channel()
    client_channel.emit('add', (1, 2))
    event = client_channel.recv()
    assert event.args == (3,)
    client_channel.close()
    srv.stop()

def test_client_server():
    endpoint = 'ipc://test_client_server'

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


def test_client_server_client_timeout():
    endpoint = 'ipc://test_client_server_client_timeout'

    class MySrv(zerorpc.Server):

        def lolita(self):
            return 42

        def add(self, a, b):
            gevent.sleep(10)
            return a + b

    srv = MySrv()
    srv.bind(endpoint)
    gevent.spawn(srv.run)

    client = zerorpc.Client(timeout=1)
    client.connect(endpoint)

    with assert_raises(zerorpc.TimeoutExpired):
        print client.add(1, 4)
    client.close()
    srv.close()

def test_client_server_exception():
    endpoint = 'ipc://test_client_server_exception'

    class MySrv(zerorpc.Server):

        def raise_something(self, a):
            return a[4]

    srv = MySrv()
    srv.bind(endpoint)
    gevent.spawn(srv.run)

    client = zerorpc.Client(timeout=1)
    client.connect(endpoint)

    with assert_raises(zerorpc.RemoteError):
        print client.raise_something(42)
    assert client.raise_something(range(5)) == 4
    client.close()
    srv.close()

def test_client_server_detailed_exception():
    endpoint = 'ipc://test_client_server_detailed_exception'

    class MySrv(zerorpc.Server):

        def raise_error(self):
            raise RuntimeError('oops!')

    srv = MySrv()
    srv.bind(endpoint)
    gevent.spawn(srv.run)

    client = zerorpc.Client(timeout=1)
    client.connect(endpoint)

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
    endpoint = 'ipc://test_exception_compat_v1'

    class MySrv(zerorpc.Server):
        pass

    srv = MySrv()
    srv.bind(endpoint)
    gevent.spawn(srv.run)

    client_events = zerorpc.Events(zmq.XREQ)
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
