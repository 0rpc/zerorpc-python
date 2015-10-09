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

import gevent

import zerorpc
from .testutils import teardown, random_ipc_endpoint, TIME_FACTOR


def test_rcp_streaming():
    endpoint = random_ipc_endpoint()

    class MySrv(zerorpc.Server):

        @zerorpc.rep
        def range(self, max_):
            return list(range(max_))

        @zerorpc.stream
        def xrange(self, max_):
            return iter(range(max_))

    srv = MySrv(heartbeat=TIME_FACTOR * 4)
    srv.bind(endpoint)
    gevent.spawn(srv.run)

    client = zerorpc.Client(heartbeat=TIME_FACTOR * 4)
    client.connect(endpoint)

    r = client.range(10)
    assert list(r) == list(range(10))

    r = client.xrange(10)
    assert getattr(r, '__next__', None) is not None
    l = []
    print('wait 4s for fun')
    gevent.sleep(TIME_FACTOR * 4)
    for x in r:
        l.append(x)
    assert l == list(range(10))
