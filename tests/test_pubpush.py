# -*- coding: utf-8 -*-


import gevent
import gevent.event

import zerorpc


def test_pushpull():
    endpoint = 'ipc://test_pushpull'

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


def test_pubsub():
    endpoint = 'ipc://test_pubsub'

    pusher = zerorpc.Publisher()
    pusher.bind(endpoint)
    trigger = gevent.event.Event()

    class Subscriber(zerorpc.Subscriber):
        def lolita(self, a, b):
            print 'lolita', a, b
            assert a + b == 3
            trigger.set()

    puller = Subscriber()
    puller.connect(endpoint)
    gevent.spawn(puller.run)

    trigger.clear()
    pusher.lolita(1, 2)
    trigger.wait()
    print 'done'
