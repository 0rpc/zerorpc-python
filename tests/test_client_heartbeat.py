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
