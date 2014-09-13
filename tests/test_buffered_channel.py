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


from nose.tools import assert_raises
import gevent
import sys

from zerorpc import zmq
import zerorpc
from testutils import teardown, random_ipc_endpoint, TIME_FACTOR


def test_close_server_bufchan():
    endpoint = random_ipc_endpoint()
    server_events = zerorpc.Events(zmq.ROUTER)
    server_events.bind(endpoint)
    server = zerorpc.ChannelMultiplexer(server_events)

    client_events = zerorpc.Events(zmq.DEALER)
    client_events.connect(endpoint)
    client = zerorpc.ChannelMultiplexer(client_events, ignore_broadcast=True)

    client_channel = client.channel()
    client_hbchan = zerorpc.HeartBeatOnChannel(client_channel, freq=TIME_FACTOR * 2)
    client_bufchan = zerorpc.BufferedChannel(client_hbchan)
    client_bufchan.emit('openthat', None)

    event = server.recv()
    server_channel = server.channel(event)
    server_hbchan = zerorpc.HeartBeatOnChannel(server_channel, freq=TIME_FACTOR * 2)
    server_bufchan = zerorpc.BufferedChannel(server_hbchan)
    server_bufchan.recv()

    gevent.sleep(TIME_FACTOR * 3)
    print 'CLOSE SERVER SOCKET!!!'
    server_bufchan.close()
    if sys.version_info < (2, 7):
        assert_raises(zerorpc.LostRemote, client_bufchan.recv)
    else:
        with assert_raises(zerorpc.LostRemote):
            client_bufchan.recv()
    print 'CLIENT LOST SERVER :)'
    client_bufchan.close()
    server.close()
    client.close()


def test_close_client_bufchan():
    endpoint = random_ipc_endpoint()
    server_events = zerorpc.Events(zmq.ROUTER)
    server_events.bind(endpoint)
    server = zerorpc.ChannelMultiplexer(server_events)

    client_events = zerorpc.Events(zmq.DEALER)
    client_events.connect(endpoint)
    client = zerorpc.ChannelMultiplexer(client_events, ignore_broadcast=True)

    client_channel = client.channel()
    client_hbchan = zerorpc.HeartBeatOnChannel(client_channel, freq=TIME_FACTOR * 2)
    client_bufchan = zerorpc.BufferedChannel(client_hbchan)
    client_bufchan.emit('openthat', None)

    event = server.recv()
    server_channel = server.channel(event)
    server_hbchan = zerorpc.HeartBeatOnChannel(server_channel, freq=TIME_FACTOR * 2)
    server_bufchan = zerorpc.BufferedChannel(server_hbchan)
    server_bufchan.recv()

    gevent.sleep(TIME_FACTOR * 3)
    print 'CLOSE CLIENT SOCKET!!!'
    client_bufchan.close()
    if sys.version_info < (2, 7):
        assert_raises(zerorpc.LostRemote, client_bufchan.recv)
    else:
        with assert_raises(zerorpc.LostRemote):
            client_bufchan.recv()
    print 'SERVER LOST CLIENT :)'
    server_bufchan.close()
    server.close()
    client.close()


def test_heartbeat_can_open_channel_server_close():
    endpoint = random_ipc_endpoint()
    server_events = zerorpc.Events(zmq.ROUTER)
    server_events.bind(endpoint)
    server = zerorpc.ChannelMultiplexer(server_events)

    client_events = zerorpc.Events(zmq.DEALER)
    client_events.connect(endpoint)
    client = zerorpc.ChannelMultiplexer(client_events, ignore_broadcast=True)

    client_channel = client.channel()
    client_hbchan = zerorpc.HeartBeatOnChannel(client_channel, freq=TIME_FACTOR * 2)
    client_bufchan = zerorpc.BufferedChannel(client_hbchan)

    event = server.recv()
    server_channel = server.channel(event)
    server_hbchan = zerorpc.HeartBeatOnChannel(server_channel, freq=TIME_FACTOR * 2)
    server_bufchan = zerorpc.BufferedChannel(server_hbchan)

    gevent.sleep(TIME_FACTOR * 3)
    print 'CLOSE SERVER SOCKET!!!'
    server_bufchan.close()
    if sys.version_info < (2, 7):
        assert_raises(zerorpc.LostRemote, client_bufchan.recv)
    else:
        with assert_raises(zerorpc.LostRemote):
            client_bufchan.recv()
    print 'CLIENT LOST SERVER :)'
    client_bufchan.close()
    server.close()
    client.close()


def test_heartbeat_can_open_channel_client_close():
    endpoint = random_ipc_endpoint()
    server_events = zerorpc.Events(zmq.ROUTER)
    server_events.bind(endpoint)
    server = zerorpc.ChannelMultiplexer(server_events)

    client_events = zerorpc.Events(zmq.DEALER)
    client_events.connect(endpoint)
    client = zerorpc.ChannelMultiplexer(client_events, ignore_broadcast=True)

    client_channel = client.channel()
    client_hbchan = zerorpc.HeartBeatOnChannel(client_channel, freq=TIME_FACTOR * 2)
    client_bufchan = zerorpc.BufferedChannel(client_hbchan)

    def server_fn():
        event = server.recv()
        server_channel = server.channel(event)
        server_hbchan = zerorpc.HeartBeatOnChannel(server_channel, freq=TIME_FACTOR * 2)
        server_bufchan = zerorpc.BufferedChannel(server_hbchan)
        try:
            while True:
                gevent.sleep(1)
        finally:
            server_bufchan.close()
    server_coro = gevent.spawn(server_fn)

    gevent.sleep(TIME_FACTOR * 3)
    print 'CLOSE CLIENT SOCKET!!!'
    client_bufchan.close()
    client.close()
    if sys.version_info < (2, 7):
        assert_raises(zerorpc.LostRemote, server_coro.get())
    else:
        with assert_raises(zerorpc.LostRemote):
            server_coro.get()
    print 'SERVER LOST CLIENT :)'
    server.close()


def test_do_some_req_rep():
    endpoint = random_ipc_endpoint()
    server_events = zerorpc.Events(zmq.ROUTER)
    server_events.bind(endpoint)
    server = zerorpc.ChannelMultiplexer(server_events)

    client_events = zerorpc.Events(zmq.DEALER)
    client_events.connect(endpoint)
    client = zerorpc.ChannelMultiplexer(client_events, ignore_broadcast=True)


    def client_do():
        client_channel = client.channel()
        client_hbchan = zerorpc.HeartBeatOnChannel(client_channel, freq=TIME_FACTOR * 2)
        client_bufchan = zerorpc.BufferedChannel(client_hbchan)
        for x in xrange(20):
            client_bufchan.emit('add', (x, x * x))
            event = client_bufchan.recv()
            assert event.name == 'OK'
            assert list(event.args) == [x + x * x]
        client_bufchan.close()

    coro_pool = gevent.pool.Pool()
    coro_pool.spawn(client_do)

    def server_do():
        event = server.recv()
        server_channel = server.channel(event)
        server_hbchan = zerorpc.HeartBeatOnChannel(server_channel, freq=TIME_FACTOR * 2)
        server_bufchan = zerorpc.BufferedChannel(server_hbchan)

        for x in xrange(20):
            event = server_bufchan.recv()
            assert event.name == 'add'
            server_bufchan.emit('OK', (sum(event.args),))
        server_bufchan.close()

    coro_pool.spawn(server_do)

    coro_pool.join()
    client.close()
    server.close()


def test_do_some_req_rep_lost_server():
    endpoint = random_ipc_endpoint()
    server_events = zerorpc.Events(zmq.ROUTER)
    server_events.bind(endpoint)
    server = zerorpc.ChannelMultiplexer(server_events)

    client_events = zerorpc.Events(zmq.DEALER)
    client_events.connect(endpoint)
    client = zerorpc.ChannelMultiplexer(client_events, ignore_broadcast=True)

    def client_do():
        print 'running'
        client_channel = client.channel()
        client_hbchan = zerorpc.HeartBeatOnChannel(client_channel, freq=TIME_FACTOR * 2)
        client_bufchan = zerorpc.BufferedChannel(client_hbchan)
        for x in xrange(10):
            client_bufchan.emit('add', (x, x * x))
            event = client_bufchan.recv()
            assert event.name == 'OK'
            assert list(event.args) == [x + x * x]
        client_bufchan.emit('add', (x, x * x))
        if sys.version_info < (2, 7):
            assert_raises(zerorpc.LostRemote, client_bufchan.recv)
        else:
            with assert_raises(zerorpc.LostRemote):
                client_bufchan.recv()
        client_bufchan.close()

    coro_pool = gevent.pool.Pool()
    coro_pool.spawn(client_do)

    def server_do():
        event = server.recv()
        server_channel = server.channel(event)
        server_hbchan = zerorpc.HeartBeatOnChannel(server_channel, freq=TIME_FACTOR * 2)
        server_bufchan = zerorpc.BufferedChannel(server_hbchan)
        for x in xrange(10):
            event = server_bufchan.recv()
            assert event.name == 'add'
            server_bufchan.emit('OK', (sum(event.args),))
        server_bufchan.close()

    coro_pool.spawn(server_do)

    coro_pool.join()
    client.close()
    server.close()


def test_do_some_req_rep_lost_client():
    endpoint = random_ipc_endpoint()
    server_events = zerorpc.Events(zmq.ROUTER)
    server_events.bind(endpoint)
    server = zerorpc.ChannelMultiplexer(server_events)

    client_events = zerorpc.Events(zmq.DEALER)
    client_events.connect(endpoint)
    client = zerorpc.ChannelMultiplexer(client_events, ignore_broadcast=True)

    def client_do():
        client_channel = client.channel()
        client_hbchan = zerorpc.HeartBeatOnChannel(client_channel, freq=TIME_FACTOR * 2)
        client_bufchan = zerorpc.BufferedChannel(client_hbchan)

        for x in xrange(10):
            client_bufchan.emit('add', (x, x * x))
            event = client_bufchan.recv()
            assert event.name == 'OK'
            assert list(event.args) == [x + x * x]
        client_bufchan.close()

    coro_pool = gevent.pool.Pool()
    coro_pool.spawn(client_do)

    def server_do():
        event = server.recv()
        server_channel = server.channel(event)
        server_hbchan = zerorpc.HeartBeatOnChannel(server_channel, freq=TIME_FACTOR * 2)
        server_bufchan = zerorpc.BufferedChannel(server_hbchan)

        for x in xrange(10):
            event = server_bufchan.recv()
            assert event.name == 'add'
            server_bufchan.emit('OK', (sum(event.args),))

        if sys.version_info < (2, 7):
            assert_raises(zerorpc.LostRemote, server_bufchan.recv)
        else:
            with assert_raises(zerorpc.LostRemote):
                server_bufchan.recv()
        server_bufchan.close()

    coro_pool.spawn(server_do)

    coro_pool.join()
    client.close()
    server.close()


def test_do_some_req_rep_client_timeout():
    endpoint = random_ipc_endpoint()
    server_events = zerorpc.Events(zmq.ROUTER)
    server_events.bind(endpoint)
    server = zerorpc.ChannelMultiplexer(server_events)

    client_events = zerorpc.Events(zmq.DEALER)
    client_events.connect(endpoint)
    client = zerorpc.ChannelMultiplexer(client_events, ignore_broadcast=True)

    def client_do():
        client_channel = client.channel()
        client_hbchan = zerorpc.HeartBeatOnChannel(client_channel, freq=TIME_FACTOR * 2)
        client_bufchan = zerorpc.BufferedChannel(client_hbchan)

        if sys.version_info < (2, 7):
            def _do_with_assert_raises():
                for x in xrange(10):
                    client_bufchan.emit('sleep', (x,))
                    event = client_bufchan.recv(timeout=TIME_FACTOR * 3)
                    assert event.name == 'OK'
                    assert list(event.args) == [x]
            assert_raises(zerorpc.TimeoutExpired, _do_with_assert_raises)
        else:
            with assert_raises(zerorpc.TimeoutExpired):
                for x in xrange(10):
                    client_bufchan.emit('sleep', (x,))
                    event = client_bufchan.recv(timeout=TIME_FACTOR * 3)
                    assert event.name == 'OK'
                    assert list(event.args) == [x]
        client_bufchan.close()

    coro_pool = gevent.pool.Pool()
    coro_pool.spawn(client_do)

    def server_do():
        event = server.recv()
        server_channel = server.channel(event)
        server_hbchan = zerorpc.HeartBeatOnChannel(server_channel, freq=TIME_FACTOR * 2)
        server_bufchan = zerorpc.BufferedChannel(server_hbchan)

        if sys.version_info < (2, 7):
            def _do_with_assert_raises():
                for x in xrange(20):
                    event = server_bufchan.recv()
                    assert event.name == 'sleep'
                    gevent.sleep(TIME_FACTOR * event.args[0])
                    server_bufchan.emit('OK', event.args)
            assert_raises(zerorpc.LostRemote, _do_with_assert_raises)
        else:
            with assert_raises(zerorpc.LostRemote):
                for x in xrange(20):
                    event = server_bufchan.recv()
                    assert event.name == 'sleep'
                    gevent.sleep(TIME_FACTOR * event.args[0])
                    server_bufchan.emit('OK', event.args)
        server_bufchan.close()


    coro_pool.spawn(server_do)

    coro_pool.join()
    client.close()
    server.close()


def test_congestion_control_server_pushing():
    endpoint = random_ipc_endpoint()
    server_events = zerorpc.Events(zmq.ROUTER)
    server_events.bind(endpoint)
    server = zerorpc.ChannelMultiplexer(server_events)

    client_events = zerorpc.Events(zmq.DEALER)
    client_events.connect(endpoint)
    client = zerorpc.ChannelMultiplexer(client_events, ignore_broadcast=True)

    read_cnt = 0

    def client_do():
        client_channel = client.channel()
        client_hbchan = zerorpc.HeartBeatOnChannel(client_channel, freq=TIME_FACTOR * 2)
        client_bufchan = zerorpc.BufferedChannel(client_hbchan, inqueue_size=100)
        for x in xrange(200):
            event = client_bufchan.recv()
            assert event.name == 'coucou'
            assert event.args == x
            global read_cnt
            read_cnt += 1
        client_bufchan.close()

    coro_pool = gevent.pool.Pool()
    coro_pool.spawn(client_do)

    def server_do():
        event = server.recv()
        server_channel = server.channel(event)
        server_hbchan = zerorpc.HeartBeatOnChannel(server_channel, freq=TIME_FACTOR * 2)
        server_bufchan = zerorpc.BufferedChannel(server_hbchan, inqueue_size=100)
        if sys.version_info < (2, 7):
            def _do_with_assert_raises():
                for x in xrange(200):
                    server_bufchan.emit('coucou', x, timeout=0)  # will fail when x == 1
            assert_raises(zerorpc.TimeoutExpired, _do_with_assert_raises)
        else:
            with assert_raises(zerorpc.TimeoutExpired):
                for x in xrange(200):
                    server_bufchan.emit('coucou', x, timeout=0)  # will fail when x == 1
        server_bufchan.emit('coucou', 1)  # block until receiver is ready
        if sys.version_info < (2, 7):
            def _do_with_assert_raises():
                for x in xrange(2, 200):
                    server_bufchan.emit('coucou', x, timeout=0)  # will fail when x == 100
            assert_raises(zerorpc.TimeoutExpired, _do_with_assert_raises)
        else:
            with assert_raises(zerorpc.TimeoutExpired):
                for x in xrange(2, 200):
                    server_bufchan.emit('coucou', x, timeout=0)  # will fail when x == 100
        for x in xrange(read_cnt, 200):
            server_bufchan.emit('coucou', x) # block until receiver is ready
        server_bufchan.close()

    coro_pool.spawn(server_do)
    try:
        coro_pool.join()
    except zerorpc.LostRemote:
        pass
    finally:
        client.close()
        server.close()
