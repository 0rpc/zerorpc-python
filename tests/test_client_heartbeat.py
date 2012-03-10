# -*- coding: utf-8 -*-


from nose.tools import assert_raises
import gevent

from zerorpc import zmq
import zerorpc

def test_client_server_hearbeat():
    endpoint = 'ipc://test_client_server_hearbeat'

    class MySrv(zerorpc.Server):

        def lolita(self):
            return 42

        def slow(self):
            gevent.sleep(10)

    srv = MySrv(heartbeat=1)
    srv.bind(endpoint)
    gevent.spawn(srv.run)

    client = zerorpc.Client(heartbeat=1)
    client.connect(endpoint)

    assert client.lolita() == 42
    print 'GOT ANSWER'


def test_client_server_activate_heartbeat():
    endpoint = 'ipc://test_client_server_activate_heartbeat'

    class MySrv(zerorpc.Server):

        def lolita(self):
            gevent.sleep(3)
            return 42

        def slow(self):
            gevent.sleep(10)

    srv = MySrv(heartbeat=1)
    srv.bind(endpoint)
    gevent.spawn(srv.run)

    client = zerorpc.Client(heartbeat=1)
    client.connect(endpoint)

    assert client.lolita() == 42
    print 'GOT ANSWER'


def test_client_server_passive_hearbeat():
    endpoint = 'ipc://test_client_server_passive_hearbeat'

    class MySrv(zerorpc.Server):

        def lolita(self):
            return 42

        def slow(self):
            gevent.sleep(3)
            return 2

    srv = MySrv(heartbeat=1)
    srv.bind(endpoint)
    gevent.spawn(srv.run)

    client = zerorpc.Client(heartbeat=1, passive_heartbeat=True)
    client.connect(endpoint)

    assert client.slow() == 2
    print 'GOT ANSWER'
