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
import gevent.event

import zerorpc


def test_pushpull_inheritance():
    endpoint = 'ipc://test_pushpull_inheritance'

    pusher = zerorpc.Pusher()
    pusher.bind(endpoint)
    trigger = gevent.event.Event()

    class Puller(zerorpc.Puller):
        def lolita(self, a, b):
            print 'lolita', a, b
            assert a + b == 3
            trigger.set()

    puller = Puller()
    puller.connect(endpoint)
    gevent.spawn(puller.run)

    trigger.clear()
    pusher.lolita(1, 2)
    trigger.wait()
    print 'done'


def test_pubsub_inheritance():
    endpoint = 'ipc://test_pubsub_inheritance'

    publisher = zerorpc.Publisher()
    publisher.bind(endpoint)
    trigger = gevent.event.Event()

    class Subscriber(zerorpc.Subscriber):
        def lolita(self, a, b):
            print 'lolita', a, b
            assert a + b == 3
            trigger.set()

    subscriber = Subscriber()
    subscriber.connect(endpoint)
    gevent.spawn(subscriber.run)

    trigger.clear()
    publisher.lolita(1, 2)
    trigger.wait()
    print 'done'


def test_pushpull_composite():
    endpoint = 'ipc://test_pushpull_composite'
    trigger = gevent.event.Event()

    class Puller(object):
        def lolita(self, a, b):
            print 'lolita', a, b
            assert a + b == 3
            trigger.set()

    pusher = zerorpc.Pusher()
    pusher.bind(endpoint)

    service = Puller()
    puller = zerorpc.Puller(service)
    puller.connect(endpoint)
    gevent.spawn(puller.run)

    trigger.clear()
    pusher.lolita(1, 2)
    trigger.wait()
    print 'done'


def test_pubsub_composite():
    endpoint = 'ipc://test_pubsub_composite'
    trigger = gevent.event.Event()

    class Subscriber(object):
        def lolita(self, a, b):
            print 'lolita', a, b
            assert a + b == 3
            trigger.set()

    publisher = zerorpc.Publisher()
    publisher.bind(endpoint)

    service = Subscriber()
    subscriber = zerorpc.Subscriber(service)
    subscriber.connect(endpoint)
    gevent.spawn(subscriber.run)

    trigger.clear()
    publisher.lolita(1, 2)
    trigger.wait()
    print 'done'
