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
import gevent.local
import gevent.queue
import gevent.event

from zerorpc import zmq


def test1():
    def server():
        c = zmq.Context()
        s = c.socket(zmq.REP)
        s.bind('tcp://0.0.0.0:9999')
        while True:
            print 'srv recving...'
            r = s.recv()
            print 'srv', r
            print 'srv sending...'
            s.send('world')

        s.close()
        c.term()

    def client():
        c = zmq.Context()
        s = c.socket(zmq.REQ)
        s.connect('tcp://localhost:9999')

        print 'cli sending...'
        s.send('hello')
        print 'cli recving...'
        r = s.recv()
        print 'cli', r

        s.close()
        c.term()

    s = gevent.spawn(server)
    c = gevent.spawn(client)
    c.join()
