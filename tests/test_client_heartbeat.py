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


import gevent

import zerorpc
from testutils import teardown, random_ipc_endpoint, TIME_FACTOR


def test_client_server_hearbeat():
    endpoint = random_ipc_endpoint()

    class MySrv(zerorpc.Server):

        def lolita(self):
            return 42

        def slow(self):
            gevent.sleep(TIME_FACTOR * 10)

    srv = MySrv(heartbeat=TIME_FACTOR * 1)
    srv.bind(endpoint)
    gevent.spawn(srv.run)

    client = zerorpc.Client(heartbeat=TIME_FACTOR * 1)
    client.connect(endpoint)

    assert client.lolita() == 42
    print 'GOT ANSWER'


def test_client_server_activate_heartbeat():
    endpoint = random_ipc_endpoint()

    class MySrv(zerorpc.Server):

        def lolita(self):
            gevent.sleep(TIME_FACTOR * 3)
            return 42

    srv = MySrv(heartbeat=TIME_FACTOR * 1)
    srv.bind(endpoint)
    gevent.spawn(srv.run)
    gevent.sleep(TIME_FACTOR * 0)

    client = zerorpc.Client(heartbeat=TIME_FACTOR * 1)
    client.connect(endpoint)

    assert client.lolita() == 42
    print 'GOT ANSWER'


def test_client_server_passive_hearbeat():
    endpoint = random_ipc_endpoint()

    class MySrv(zerorpc.Server):

        def lolita(self):
            return 42

        def slow(self):
            gevent.sleep(TIME_FACTOR * 3)
            return 2

    srv = MySrv(heartbeat=TIME_FACTOR * 1)
    srv.bind(endpoint)
    gevent.spawn(srv.run)

    client = zerorpc.Client(heartbeat=TIME_FACTOR * 1, passive_heartbeat=True)
    client.connect(endpoint)

    assert client.slow() == 2
    print 'GOT ANSWER'


def test_client_hb_doesnt_linger_on_streaming():
    endpoint = random_ipc_endpoint()

    class MySrv(zerorpc.Server):

        @zerorpc.stream
        def iter(self):
            return xrange(42)

    srv = MySrv(heartbeat=TIME_FACTOR * 1, context=zerorpc.Context())
    srv.bind(endpoint)
    gevent.spawn(srv.run)

    client1 = zerorpc.Client(endpoint, heartbeat=TIME_FACTOR * 1, context=zerorpc.Context())

    def test_client():
        assert list(client1.iter()) == list(xrange(42))
        print 'sleep 3s'
        gevent.sleep(TIME_FACTOR * 3)

    gevent.spawn(test_client).join()


def est_client_drop_few():
    endpoint = random_ipc_endpoint()

    class MySrv(zerorpc.Server):

        def lolita(self):
            return 42

    srv = MySrv(heartbeat=TIME_FACTOR * 1, context=zerorpc.Context())
    srv.bind(endpoint)
    gevent.spawn(srv.run)

    client1 = zerorpc.Client(endpoint, heartbeat=TIME_FACTOR * 1, context=zerorpc.Context())
    client2 = zerorpc.Client(endpoint, heartbeat=TIME_FACTOR * 1, context=zerorpc.Context())
    client3 = zerorpc.Client(endpoint, heartbeat=TIME_FACTOR * 1, context=zerorpc.Context())

    assert client1.lolita() == 42
    assert client2.lolita() == 42

    gevent.sleep(TIME_FACTOR * 3)
    assert client3.lolita() == 42


def test_client_drop_empty_stream():
    endpoint = random_ipc_endpoint()

    class MySrv(zerorpc.Server):

        @zerorpc.stream
        def iter(self):
            return []

    srv = MySrv(heartbeat=TIME_FACTOR * 1, context=zerorpc.Context())
    srv.bind(endpoint)
    gevent.spawn(srv.run)

    client1 = zerorpc.Client(endpoint, heartbeat=TIME_FACTOR * 1, context=zerorpc.Context())

    def test_client():
        print 'grab iter'
        i = client1.iter()

        print 'sleep 3s'
        gevent.sleep(TIME_FACTOR * 3)

    gevent.spawn(test_client).join()


def test_client_drop_stream():
    endpoint = random_ipc_endpoint()

    class MySrv(zerorpc.Server):

        @zerorpc.stream
        def iter(self):
            return xrange(500)

    srv = MySrv(heartbeat=TIME_FACTOR * 1, context=zerorpc.Context())
    srv.bind(endpoint)
    gevent.spawn(srv.run)

    client1 = zerorpc.Client(endpoint, heartbeat=TIME_FACTOR * 1, context=zerorpc.Context())

    def test_client():
        print 'grab iter'
        i = client1.iter()

        print 'consume some'
        assert list(next(i) for x in xrange(142)) == list(xrange(142))

        print 'sleep 3s'
        gevent.sleep(TIME_FACTOR * 3)

    gevent.spawn(test_client).join()
