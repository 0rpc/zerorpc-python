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
from builtins import range

import pytest
import gevent
import sys

from zerorpc import zmq
import zerorpc
from .testutils import teardown, random_ipc_endpoint, TIME_FACTOR


def test_close_server_hbchan():
    endpoint = random_ipc_endpoint()
    server_events = zerorpc.Events(zmq.ROUTER)
    server_events.bind(endpoint)
    server = zerorpc.ChannelMultiplexer(server_events)

    client_events = zerorpc.Events(zmq.DEALER)
    client_events.connect(endpoint)
    client = zerorpc.ChannelMultiplexer(client_events, ignore_broadcast=True)

    client_channel = client.channel()
    client_hbchan = zerorpc.HeartBeatOnChannel(client_channel, freq=TIME_FACTOR * 2)
    client_hbchan.emit('openthat', None)

    event = server.recv()
    server_channel = server.channel(event)
    server_hbchan = zerorpc.HeartBeatOnChannel(server_channel, freq=TIME_FACTOR * 2)
    server_hbchan.recv()

    gevent.sleep(TIME_FACTOR * 3)
    print('CLOSE SERVER SOCKET!!!')
    server_hbchan.close()
    with pytest.raises(zerorpc.LostRemote):
        client_hbchan.recv()
    print('CLIENT LOST SERVER :)')
    client_hbchan.close()
    server.close()
    client.close()


def test_close_client_hbchan():
    endpoint = random_ipc_endpoint()
    server_events = zerorpc.Events(zmq.ROUTER)
    server_events.bind(endpoint)
    server = zerorpc.ChannelMultiplexer(server_events)

    client_events = zerorpc.Events(zmq.DEALER)
    client_events.connect(endpoint)
    client = zerorpc.ChannelMultiplexer(client_events, ignore_broadcast=True)

    client_channel = client.channel()
    client_hbchan = zerorpc.HeartBeatOnChannel(client_channel, freq=TIME_FACTOR * 2)
    client_hbchan.emit('openthat', None)

    event = server.recv()
    server_channel = server.channel(event)
    server_hbchan = zerorpc.HeartBeatOnChannel(server_channel, freq=TIME_FACTOR * 2)
    server_hbchan.recv()

    gevent.sleep(TIME_FACTOR * 3)
    print('CLOSE CLIENT SOCKET!!!')
    client_hbchan.close()
    with pytest.raises(zerorpc.LostRemote):
        server_hbchan.recv()
    print('SERVER LOST CLIENT :)')
    server_hbchan.close()
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

    event = server.recv()
    server_channel = server.channel(event)
    server_hbchan = zerorpc.HeartBeatOnChannel(server_channel, freq=TIME_FACTOR * 2)

    gevent.sleep(TIME_FACTOR * 3)
    print('CLOSE SERVER SOCKET!!!')
    server_hbchan.close()
    with pytest.raises(zerorpc.LostRemote):
        client_hbchan.recv()
    print('CLIENT LOST SERVER :)')
    client_hbchan.close()
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

    event = server.recv()
    server_channel = server.channel(event)
    server_hbchan = zerorpc.HeartBeatOnChannel(server_channel, freq=TIME_FACTOR * 2)

    gevent.sleep(TIME_FACTOR * 3)
    print('CLOSE CLIENT SOCKET!!!')
    client_hbchan.close()
    client.close()
    with pytest.raises(zerorpc.LostRemote):
        server_hbchan.recv()
    print('SERVER LOST CLIENT :)')
    server_hbchan.close()
    server.close()


def test_do_some_req_rep():
    endpoint = random_ipc_endpoint()
    server_events = zerorpc.Events(zmq.ROUTER)
    server_events.bind(endpoint)
    server = zerorpc.ChannelMultiplexer(server_events)

    client_events = zerorpc.Events(zmq.DEALER)
    client_events.connect(endpoint)
    client = zerorpc.ChannelMultiplexer(client_events, ignore_broadcast=True)

    client_channel = client.channel()
    client_hbchan = zerorpc.HeartBeatOnChannel(client_channel, freq=TIME_FACTOR * 4)

    event = server.recv()
    server_channel = server.channel(event)
    server_hbchan = zerorpc.HeartBeatOnChannel(server_channel, freq=TIME_FACTOR * 4)

    def client_do():
        for x in range(20):
            client_hbchan.emit('add', (x, x * x))
            event = client_hbchan.recv()
            assert event.name == 'OK'
            assert list(event.args) == [x + x * x]
        client_hbchan.close()

    client_task = gevent.spawn(client_do)

    def server_do():
        for x in range(20):
            event = server_hbchan.recv()
            assert event.name == 'add'
            server_hbchan.emit('OK', (sum(event.args),))
        server_hbchan.close()

    server_task = gevent.spawn(server_do)

    server_task.get()
    client_task.get()
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
        print('running')
        client_channel = client.channel()
        client_hbchan = zerorpc.HeartBeatOnChannel(client_channel, freq=TIME_FACTOR * 2)
        for x in range(10):
            client_hbchan.emit('add', (x, x * x))
            event = client_hbchan.recv()
            assert event.name == 'OK'
            assert list(event.args) == [x + x * x]
        client_hbchan.emit('add', (x, x * x))
        with pytest.raises(zerorpc.LostRemote):
            client_hbchan.recv()
        client_hbchan.close()

    client_task = gevent.spawn(client_do)

    def server_do():
        event = server.recv()
        server_channel = server.channel(event)
        server_hbchan = zerorpc.HeartBeatOnChannel(server_channel, freq=TIME_FACTOR * 2)
        for x in range(10):
            event = server_hbchan.recv()
            assert event.name == 'add'
            server_hbchan.emit('OK', (sum(event.args),))
        server_hbchan.close()

    server_task = gevent.spawn(server_do)

    server_task.get()
    client_task.get()
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

        for x in range(10):
            client_hbchan.emit('add', (x, x * x))
            event = client_hbchan.recv()
            assert event.name == 'OK'
            assert list(event.args) == [x + x * x]
        client_hbchan.close()

    client_task = gevent.spawn(client_do)

    def server_do():
        event = server.recv()
        server_channel = server.channel(event)
        server_hbchan = zerorpc.HeartBeatOnChannel(server_channel, freq=TIME_FACTOR * 2)

        for x in range(10):
            event = server_hbchan.recv()
            assert event.name == 'add'
            server_hbchan.emit('OK', (sum(event.args),))

        with pytest.raises(zerorpc.LostRemote):
            server_hbchan.recv()
        server_hbchan.close()

    server_task = gevent.spawn(server_do)

    server_task.get()
    client_task.get()
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

        with pytest.raises(zerorpc.TimeoutExpired):
            for x in range(10):
                client_hbchan.emit('sleep', (x,))
                event = client_hbchan.recv(timeout=TIME_FACTOR * 3)
                assert event.name == 'OK'
                assert list(event.args) == [x]
        client_hbchan.close()

    client_task = gevent.spawn(client_do)

    def server_do():
        event = server.recv()
        server_channel = server.channel(event)
        server_hbchan = zerorpc.HeartBeatOnChannel(server_channel, freq=TIME_FACTOR * 2)

        with pytest.raises(zerorpc.LostRemote):
            for x in range(20):
                event = server_hbchan.recv()
                assert event.name == 'sleep'
                gevent.sleep(TIME_FACTOR * event.args[0])
                server_hbchan.emit('OK', event.args)
        server_hbchan.close()

    server_task = gevent.spawn(server_do)

    server_task.get()
    client_task.get()
    client.close()
    server.close()
