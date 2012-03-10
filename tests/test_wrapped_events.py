# -*- coding: utf-8 -*-


from nose.tools import assert_raises
import gevent
import random

from zerorpc import zmq
import zerorpc

def test_sub_events():
    endpoint = 'ipc://test_sub_events'
    server_events = zerorpc.Events(zmq.XREP)
    server_events.bind(endpoint)
    server = zerorpc.ChannelMultiplexer(server_events)

    client_events = zerorpc.Events(zmq.XREQ)
    client_events.connect(endpoint)
    client = zerorpc.ChannelMultiplexer(client_events, ignore_broadcast=True)

    client_channel = client.channel()
    client_channel_events = zerorpc.WrappedEvents(client_channel)
    client_channel_events.emit('coucou', 42)

    event = server.recv()
    print event
    assert type(event.args) is str
    assert event.name == 'w'
    subevent = zerorpc.Event.unpack(event.args)
    print 'subevent:', subevent
    server_channel = server.channel(event)
    server_channel_events = zerorpc.WrappedEvents(server_channel)
    server_channel_channel = zerorpc.ChannelMultiplexer(server_channel_events)
    event = server_channel_channel.recv()
    print event
    assert event.name == 'coucou'
    assert event.args == 42

    server_events.close()
    client_events.close()

def test_multiple_sub_events():
    endpoint = 'ipc://test_multiple_sub_events'
    server_events = zerorpc.Events(zmq.XREP)
    server_events.bind(endpoint)
    server = zerorpc.ChannelMultiplexer(server_events)

    client_events = zerorpc.Events(zmq.XREQ)
    client_events.connect(endpoint)
    client = zerorpc.ChannelMultiplexer(client_events, ignore_broadcast=True)

    client_channel1 = client.channel()
    client_channel_events1 = zerorpc.WrappedEvents(client_channel1)
    client_channel2 = client.channel()
    client_channel_events2 = zerorpc.WrappedEvents(client_channel2)
    client_channel_events1.emit('coucou1', 43)
    client_channel_events2.emit('coucou2', 44)
    client_channel_events2.emit('another', 42)

    event = server.recv()
    print event
    assert type(event.args) is str
    assert event.name == 'w'
    subevent = zerorpc.Event.unpack(event.args)
    print 'subevent:', subevent
    server_channel = server.channel(event)
    server_channel_events = zerorpc.WrappedEvents(server_channel)
    event = server_channel_events.recv()
    print event
    assert event.name == 'coucou1'
    assert event.args == 43


    event = server.recv()
    print event
    assert type(event.args) is str
    assert event.name == 'w'
    subevent = zerorpc.Event.unpack(event.args)
    print 'subevent:', subevent
    server_channel = server.channel(event)
    server_channel_events = zerorpc.WrappedEvents(server_channel)
    event = server_channel_events.recv()
    print event
    assert event.name == 'coucou2'
    assert event.args == 44

    event = server_channel_events.recv()
    print event
    assert event.name == 'another'
    assert event.args == 42

    server_events.close()
    client_events.close()

def test_recursive_multiplexer():
    endpoint = 'ipc://test_recursive_multiplexer'

    server_events = zerorpc.Events(zmq.XREP)
    server_events.bind(endpoint)
    servermux = zerorpc.ChannelMultiplexer(server_events)

    client_events = zerorpc.Events(zmq.XREQ)
    client_events.connect(endpoint)
    clientmux = zerorpc.ChannelMultiplexer(client_events, ignore_broadcast=True)

    def ping_pong(climux, srvmux):
        cli_chan = climux.channel()
        someid = random.randint(0, 1000000)
        print 'ping...'
        cli_chan.emit('ping', someid)
        print 'srv_chan got:'
        event = srvmux.recv()
        srv_chan = srvmux.channel(event)
        print event
        assert event.name == 'ping'
        assert event.args == someid
        print 'pong...'
        srv_chan.emit('pong', someid)
        print 'cli_chan got:'
        event = cli_chan.recv()
        print event
        assert event.name == 'pong'
        assert event.args == someid
        srv_chan.close()
        cli_chan.close()

    def create_sub_multiplexer(events, from_event=None, ignore_broadcast=False):
        channel = events.channel(from_event)
        sub_events = zerorpc.WrappedEvents(channel)
        sub_multiplexer = zerorpc.ChannelMultiplexer(sub_events,
                ignore_broadcast=ignore_broadcast)
        return sub_multiplexer

    def open_sub_multiplexer(climux, srvmux):
        someid = random.randint(0, 1000000)
        print 'open...'
        clisubmux = create_sub_multiplexer(climux, ignore_broadcast=True)
        clisubmux.emit('open that', someid)
        print 'srvsubmux got:'
        event = srvmux.recv()
        assert event.name == 'w'
        srvsubmux = create_sub_multiplexer(srvmux, event)
        event = srvsubmux.recv()
        print event
        return (clisubmux, srvsubmux)

    ping_pong(clientmux, servermux)

    (clientmux_lv2, servermux_lv2) = open_sub_multiplexer(clientmux, servermux)
    ping_pong(clientmux_lv2, servermux_lv2)

    (clientmux_lv3, servermux_lv3) = open_sub_multiplexer(clientmux_lv2,
            servermux_lv2)
    ping_pong(clientmux_lv3, servermux_lv3)

    (clientmux_lv4, servermux_lv4) = open_sub_multiplexer(clientmux_lv3,
            servermux_lv3)
    ping_pong(clientmux_lv4, servermux_lv4)

    ping_pong(clientmux_lv4, servermux_lv4)
    ping_pong(clientmux_lv3, servermux_lv3)
    ping_pong(clientmux_lv2, servermux_lv2)
    ping_pong(clientmux, servermux)
    ping_pong(clientmux, servermux)
    ping_pong(clientmux_lv2, servermux_lv2)
    ping_pong(clientmux_lv4, servermux_lv4)
    ping_pong(clientmux_lv3, servermux_lv3)

    (clientmux_lv5, servermux_lv5) = open_sub_multiplexer(clientmux_lv4,
            servermux_lv4)
    ping_pong(clientmux_lv5, servermux_lv5)
