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
import gevent

from zerorpc import zmq
from .testutils import teardown, random_ipc_endpoint


def test1():
    endpoint = random_ipc_endpoint()
    def server():
        c = zmq.Context()
        s = c.socket(zmq.REP)
        s.bind(endpoint)
        while True:
            print(b'srv recving...')
            r = s.recv()
            print('srv', r)
            print('srv sending...')
            s.send(b'world')

        s.close()
        c.term()

    def client():
        c = zmq.Context()
        s = c.socket(zmq.REQ)
        s.connect(endpoint)

        print('cli sending...')
        s.send(b'hello')
        print('cli recving...')
        r = s.recv()
        print('cli', r)

        s.close()
        c.term()

    s = gevent.spawn(server)
    c = gevent.spawn(client)
    c.join()
