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

from zerorpc import zmq
import zerorpc


#def test_close_server_bufchan():
#    endpoint = 'ipc://test_close_server_bufchan_'
#    server_events = zerorpc.Events(zmq.XREP)
#    server_events.bind(endpoint)
#    server = zerorpc.ChannelMultiplexer(server_events)

#    client_events = zerorpc.Events(zmq.XREQ)
#    client_events.connect(endpoint)
#    client = zerorpc.ChannelMultiplexer(client_events, ignore_broadcast=True)

#    client_channel = client.channel()
#    client_hbchan = zerorpc.HeartBeatOnChannel(client_channel, freq=1)
#    client_bufchan = zerorpc.BufferedChannel(client_hbchan)
#    client_bufchan.emit('openthat', None)

#    event = server.recv()
#    server_channel = server.channel(event)
#    server_hbchan = zerorpc.HeartBeatOnChannel(server_channel, freq=1)
#    server_bufchan = zerorpc.BufferedChannel(server_hbchan)
#    server_bufchan.recv()

#    gevent.sleep(3)
#    print 'CLOSE SERVER SOCKET!!!'
#    server_bufchan.close()
#    server_hbchan.close()
#    server_channel.close()
#    with assert_raises(zerorpc.LostRemote):
#        client_bufchan.recv()
#    print 'CLIENT LOST SERVER :)'
#    client_bufchan.close()
#    client_hbchan.close()
#    client_channel.close()
#    server.close()
#    client.close()


#def test_close_client_bufchan():
#    endpoint = 'ipc://test_close_client_bufchan_'
#    server_events = zerorpc.Events(zmq.XREP)
#    server_events.bind(endpoint)
#    server = zerorpc.ChannelMultiplexer(server_events)

#    client_events = zerorpc.Events(zmq.XREQ)
#    client_events.connect(endpoint)
#    client = zerorpc.ChannelMultiplexer(client_events, ignore_broadcast=True)

#    client_channel = client.channel()
#    client_hbchan = zerorpc.HeartBeatOnChannel(client_channel, freq=1)
#    client_bufchan = zerorpc.BufferedChannel(client_hbchan)
#    client_bufchan.emit('openthat', None)

#    event = server.recv()
#    server_channel = server.channel(event)
#    server_hbchan = zerorpc.HeartBeatOnChannel(server_channel, freq=1)
#    server_bufchan = zerorpc.BufferedChannel(server_hbchan)
#    server_bufchan.recv()

#    gevent.sleep(3)
#    print 'CLOSE CLIENT SOCKET!!!'
#    client_bufchan.close()
#    server_hbchan.close()
#    client_channel.close()
#    with assert_raises(zerorpc.LostRemote):
#        server_bufchan.recv()
#    print 'SERVER LOST CLIENT :)'
#    server_bufchan.close()
#    client_hbchan.close()
#    server_channel.close()
#    server.close()
#    client.close()


#def test_heartbeat_can_open_channel_server_close():
#    endpoint = 'ipc://test_heartbeat_can_open_channel_server_close_'
#    server_events = zerorpc.Events(zmq.XREP)
#    server_events.bind(endpoint)
#    server = zerorpc.ChannelMultiplexer(server_events)

#    client_events = zerorpc.Events(zmq.XREQ)
#    client_events.connect(endpoint)
#    client = zerorpc.ChannelMultiplexer(client_events, ignore_broadcast=True)

#    client_channel = client.channel()
#    client_hbchan = zerorpc.HeartBeatOnChannel(client_channel, freq=1)
#    client_bufchan = zerorpc.BufferedChannel(client_hbchan)

#    event = server.recv()
#    server_channel = server.channel(event)
#    server_hbchan = zerorpc.HeartBeatOnChannel(server_channel, freq=1)
#    server_bufchan = zerorpc.BufferedChannel(server_hbchan)

#    gevent.sleep(3)
#    print 'CLOSE SERVER SOCKET!!!'
#    server_bufchan.close()
#    server_hbchan.close()
#    server_channel.close()
#    with assert_raises(zerorpc.LostRemote):
#        client_bufchan.recv()
#    print 'CLIENT LOST SERVER :)'
#    client_bufchan.close()
#    client_hbchan.close()
#    client_channel.close()
#    server.close()
#    client.close()


#def test_heartbeat_can_open_channel_client_close():
#    endpoint = 'ipc://test_heartbeat_can_open_channel_client_close_'
#    server_events = zerorpc.Events(zmq.XREP)
#    server_events.bind(endpoint)
#    server = zerorpc.ChannelMultiplexer(server_events)

#    client_events = zerorpc.Events(zmq.XREQ)
#    client_events.connect(endpoint)
#    client = zerorpc.ChannelMultiplexer(client_events, ignore_broadcast=True)

#    client_channel = client.channel()
#    client_hbchan = zerorpc.HeartBeatOnChannel(client_channel, freq=1)
#    client_bufchan = zerorpc.BufferedChannel(client_hbchan)

#    event = server.recv()
#    server_channel = server.channel(event)
#    server_hbchan = zerorpc.HeartBeatOnChannel(server_channel, freq=1)
#    server_bufchan = zerorpc.BufferedChannel(server_hbchan)

#    gevent.sleep(3)
#    print 'CLOSE CLIENT SOCKET!!!'
#    client_bufchan.close()
#    server_hbchan.close()
#    client_channel.close()
#    client.close()
#    with assert_raises(zerorpc.LostRemote):
#        server_bufchan.recv()
#    print 'SERVER LOST CLIENT :)'
#    server_bufchan.close()
#    client_hbchan.close()
#    server_channel.close()
#    server.close()


#def test_do_some_req_rep():
#    endpoint = 'ipc://test_do_some_req_rep_'
#    server_events = zerorpc.Events(zmq.XREP)
#    server_events.bind(endpoint)
#    server = zerorpc.ChannelMultiplexer(server_events)

#    client_events = zerorpc.Events(zmq.XREQ)
#    client_events.connect(endpoint)
#    client = zerorpc.ChannelMultiplexer(client_events, ignore_broadcast=True)

#    client_channel = client.channel()
#    client_hbchan = zerorpc.HeartBeatOnChannel(client_channel, freq=1)
#    client_bufchan = zerorpc.BufferedChannel(client_hbchan)

#    event = server.recv()
#    server_channel = server.channel(event)
#    server_hbchan = zerorpc.HeartBeatOnChannel(server_channel, freq=1)
#    server_bufchan = zerorpc.BufferedChannel(server_hbchan)

#    def client_do():
#        for x in xrange(20):
#            client_bufchan.emit('add', (x, x * x))
#            event = client_bufchan.recv()
#            assert event.name == 'OK'
#            assert event.args == (x + x * x,)
#        client_bufchan.close()
#        client_hbchan.close()
#        client_channel.close()

#    client_task = gevent.spawn(client_do)

#    def server_do():
#        for x in xrange(20):
#            event = server_bufchan.recv()
#            assert event.name == 'add'
#            server_bufchan.emit('OK', (sum(event.args),))
#        server_bufchan.close()
#        server_hbchan.close()
#        server_channel.close()

#    server_task = gevent.spawn(server_do)

#    server_task.get()
#    client_task.get()
#    client.close()
#    server.close()


#def test_do_some_req_rep_lost_server():
#    endpoint = 'ipc://test_do_some_req_rep_lost_server_'
#    server_events = zerorpc.Events(zmq.XREP)
#    server_events.bind(endpoint)
#    server = zerorpc.ChannelMultiplexer(server_events)

#    client_events = zerorpc.Events(zmq.XREQ)
#    client_events.connect(endpoint)
#    client = zerorpc.ChannelMultiplexer(client_events, ignore_broadcast=True)

#    def client_do():
#        print 'running'
#        client_channel = client.channel()
#        client_hbchan = zerorpc.HeartBeatOnChannel(client_channel, freq=1)
#        client_bufchan = zerorpc.BufferedChannel(client_hbchan)
#        for x in xrange(10):
#            client_bufchan.emit('add', (x, x * x))
#            event = client_bufchan.recv()
#            assert event.name == 'OK'
#            assert event.args == (x + x * x,)
#        client_bufchan.emit('add', (x, x * x))
#        with assert_raises(zerorpc.LostRemote):
#            event = client_bufchan.recv()
#        client_bufchan.close()
#        client_hbchan.close()
#        client_channel.close()

#    client_task = gevent.spawn(client_do)

#    def server_do():
#        event = server.recv()
#        server_channel = server.channel(event)
#        server_hbchan = zerorpc.HeartBeatOnChannel(server_channel, freq=1)
#        server_bufchan = zerorpc.BufferedChannel(server_hbchan)
#        for x in xrange(10):
#            event = server_bufchan.recv()
#            assert event.name == 'add'
#            server_bufchan.emit('OK', (sum(event.args),))
#        server_bufchan.close()
#        server_hbchan.close()
#        server_channel.close()

#    server_task = gevent.spawn(server_do)

#    server_task.get()
#    client_task.get()
#    client.close()
#    server.close()


#def test_do_some_req_rep_lost_client():
#    endpoint = 'ipc://test_do_some_req_rep_lost_client_'
#    server_events = zerorpc.Events(zmq.XREP)
#    server_events.bind(endpoint)
#    server = zerorpc.ChannelMultiplexer(server_events)

#    client_events = zerorpc.Events(zmq.XREQ)
#    client_events.connect(endpoint)
#    client = zerorpc.ChannelMultiplexer(client_events, ignore_broadcast=True)

#    def client_do():
#        client_channel = client.channel()
#        client_hbchan = zerorpc.HeartBeatOnChannel(client_channel, freq=1)
#        client_bufchan = zerorpc.BufferedChannel(client_hbchan)

#        for x in xrange(10):
#            client_bufchan.emit('add', (x, x * x))
#            event = client_bufchan.recv()
#            assert event.name == 'OK'
#            assert event.args == (x + x * x,)
#        client_bufchan.close()
#        client_channel.close()

#    client_task = gevent.spawn(client_do)

#    def server_do():
#        event = server.recv()
#        server_channel = server.channel(event)
#        server_hbchan = zerorpc.HeartBeatOnChannel(server_channel, freq=1)
#        server_bufchan = zerorpc.BufferedChannel(server_hbchan)

#        for x in xrange(10):
#            event = server_bufchan.recv()
#            assert event.name == 'add'
#            server_bufchan.emit('OK', (sum(event.args),))

#        with assert_raises(zerorpc.LostRemote):
#            event = server_bufchan.recv()
#        server_bufchan.close()
#        server_channel.close()

#    server_task = gevent.spawn(server_do)

#    server_task.get()
#    client_task.get()
#    client.close()
#    server.close()


#def test_do_some_req_rep_client_timeout():
#    endpoint = 'ipc://test_do_some_req_rep_client_timeout_'
#    server_events = zerorpc.Events(zmq.XREP)
#    server_events.bind(endpoint)
#    server = zerorpc.ChannelMultiplexer(server_events)

#    client_events = zerorpc.Events(zmq.XREQ)
#    client_events.connect(endpoint)
#    client = zerorpc.ChannelMultiplexer(client_events, ignore_broadcast=True)

#    def client_do():
#        client_channel = client.channel()
#        client_hbchan = zerorpc.HeartBeatOnChannel(client_channel, freq=1)
#        client_bufchan = zerorpc.BufferedChannel(client_hbchan)

#        with assert_raises(zerorpc.TimeoutExpired):
#            for x in xrange(10):
#                client_bufchan.emit('sleep', (x,))
#                event = client_bufchan.recv(timeout=3)
#                assert event.name == 'OK'
#                assert event.args == (x,)
#        client_bufchan.close()
#        client_channel.close()

#    client_task = gevent.spawn(client_do)

#    def server_do():
#        event = server.recv()
#        server_channel = server.channel(event)
#        server_hbchan = zerorpc.HeartBeatOnChannel(server_channel, freq=1)
#        server_bufchan = zerorpc.BufferedChannel(server_hbchan)

#        with assert_raises(zerorpc.LostRemote):
#            for x in xrange(20):
#                event = server_bufchan.recv()
#                assert event.name == 'sleep'
#                gevent.sleep(event.args[0])
#                server_bufchan.emit('OK', event.args)
#        server_bufchan.close()
#        server_channel.close()

#    server_task = gevent.spawn(server_do)

#    server_task.get()
#    client_task.get()
#    client.close()
#    server.close()


class CongestionError(Exception):
    pass


def test_congestion_control_server_pushing():
    endpoint = 'ipc://test_congestion_control_server_pushing_'
    server_events = zerorpc.Events(zmq.XREP)
    server_events.bind(endpoint)
    server = zerorpc.ChannelMultiplexer(server_events)

    client_events = zerorpc.Events(zmq.XREQ)
    client_events.connect(endpoint)
    client = zerorpc.ChannelMultiplexer(client_events, ignore_broadcast=True)

    client_channel = client.channel()
    client_hbchan = zerorpc.HeartBeatOnChannel(client_channel, freq=1)
    client_bufchan = zerorpc.BufferedChannel(client_hbchan)

    event = server.recv()
    server_channel = server.channel(event)
    server_hbchan = zerorpc.HeartBeatOnChannel(server_channel, freq=1)
    server_bufchan = zerorpc.BufferedChannel(server_hbchan)

    def client_do():
        for x in xrange(200):
            event = client_bufchan.recv()
            assert event.name == 'coucou'
            assert event.args == x

    client_task = gevent.spawn(client_do)

    def server_do():
        with assert_raises(CongestionError):
            for x in xrange(200):
                if server_bufchan.emit('coucou', x, block=False) == False:
                    raise CongestionError()  # will fail when x == 1
        server_bufchan.emit('coucou', 1)  # block until receiver is ready
        with assert_raises(CongestionError):
            for x in xrange(2, 200):
                if server_bufchan.emit('coucou', x, block=False) == False:
                    raise CongestionError()  # will fail when x == 100
        for x in xrange(101, 200):
            server_bufchan.emit('coucou', x) # block until receiver is ready

    server_task = gevent.spawn(server_do)

    server_task.get()
    client_task.get()
    client_bufchan.close()
    client_hbchan.close()
    client.close()
    server_task.get()
    server_bufchan.close()
    server_hbchan.close()
    server.close()
