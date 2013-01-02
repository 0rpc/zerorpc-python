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

from testutils import teardown, random_ipc_endpoint


def test_pushpull_inheritance():
    endpoint = random_ipc_endpoint()

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
    endpoint = random_ipc_endpoint()

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
    # We need this retry logic to wait that the subscriber.run coroutine starts
    # reading (the published messages will go to /dev/null until then).
    for attempt in xrange(0, 10):
        publisher.lolita(1, 2)
        if trigger.wait(0.2):
            print 'done'
            return

    raise RuntimeError("The subscriber didn't receive any published message")

def test_pushpull_composite():
    endpoint = random_ipc_endpoint()
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
    endpoint = random_ipc_endpoint()
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
    # We need this retry logic to wait that the subscriber.run coroutine starts
    # reading (the published messages will go to /dev/null until then).
    for attempt in xrange(0, 10):
        publisher.lolita(1, 2)
        if trigger.wait(0.2):
            print 'done'
            return

    raise RuntimeError("The subscriber didn't receive any published message")
