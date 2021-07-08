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


from __future__ import print_function
from __future__ import absolute_import
from nose.tools import assert_raises
import gevent
import sys

from zerorpc import zmq
import zerorpc
from .testutils import teardown, random_ipc_endpoint, TIME_FACTOR


def test_client_server_client_timeout_with_async():
    endpoint = random_ipc_endpoint()

    class MySrv(zerorpc.Server):

        def lolita(self):
            return 42

        def add(self, a, b):
            gevent.sleep(TIME_FACTOR * 10)
            return a + b

    srv = MySrv()
    srv.bind(endpoint)
    gevent.spawn(srv.run)

    client = zerorpc.Client(timeout=TIME_FACTOR * 2)
    client.connect(endpoint)

    async_result = client.add(1, 4, **{"async": True})

    if sys.version_info < (2, 7):
        def _do_with_assert_raises():
            print(async_result.get())
        assert_raises(zerorpc.TimeoutExpired, _do_with_assert_raises)
    else:
        with assert_raises(zerorpc.TimeoutExpired):
            print(async_result.get())
    client.close()
    srv.close()


def test_client_server_with_async():
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

    async_result = client.lolita(**{"async": True})
    assert async_result.get() == 42

    async_result = client.add(1, 4, **{"async": True})
    assert async_result.get() == 5
