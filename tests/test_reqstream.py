# -*- coding: utf-8 -*-


from nose.tools import assert_raises
import gevent

from zerorpc import zmq
import zerorpc

def test_rcp_streaming():
    endpoint = 'ipc://test_rcp_streaming'

    class MySrv(zerorpc.Server):

        @zerorpc.rep
        def range(self, max):
            return xrange(max)

        @zerorpc.stream
        def xrange(self, max):
            return xrange(max)

    srv = MySrv(heartbeat=2)
    srv.bind(endpoint)
    gevent.spawn(srv.run)

    client = zerorpc.Client(heartbeat=2)
    client.connect(endpoint)

    r = client.range(10)
    assert r == tuple(range(10))

    r = client.xrange(10)
    assert getattr(r, 'next', None) is not None
    l = []
    print 'wait 4s for fun'
    gevent.sleep(4)
    for x in r:
        l.append(x)
    assert l == range(10)
