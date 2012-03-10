# -*- coding: utf-8 -*-


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
