# -*- coding: utf-8 -*-


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
