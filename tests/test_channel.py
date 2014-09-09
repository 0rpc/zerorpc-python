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


from zerorpc import zmq
import zerorpc
from testutils import teardown, random_ipc_endpoint


def test_events_channel_client_side():
    endpoint = random_ipc_endpoint()
    server_events = zerorpc.Events(zmq.ROUTER)
    server_events.bind(endpoint)
    server = zerorpc.ChannelMultiplexer(server_events)

    client_events = zerorpc.Events(zmq.DEALER)
    client_events.connect(endpoint)
    client = zerorpc.ChannelMultiplexer(client_events)

    client_channel = client.channel()
    client_channel.emit('someevent', (42,))

    event = server.recv()
    print event
    assert list(event.args) == [42]
    assert event.identity is not None

    reply_event = server.new_event('someanswer', (21,),
            xheader=dict(response_to=event.header['message_id']))
    reply_event.identity = event.identity
    server.emit_event(reply_event)
    event = client_channel.recv()
    assert list(event.args) == [21]


def test_events_channel_client_side_server_send_many():
    endpoint = random_ipc_endpoint()
    server_events = zerorpc.Events(zmq.ROUTER)
    server_events.bind(endpoint)
    server = zerorpc.ChannelMultiplexer(server_events)

    client_events = zerorpc.Events(zmq.DEALER)
    client_events.connect(endpoint)
    client = zerorpc.ChannelMultiplexer(client_events)

    client_channel = client.channel()
    client_channel.emit('giveme', (10,))

    event = server.recv()
    print event
    assert list(event.args) == [10]
    assert event.identity is not None

    for x in xrange(10):
        reply_event = server.new_event('someanswer', (x,),
                xheader=dict(response_to=event.header['message_id']))
        reply_event.identity = event.identity
        server.emit_event(reply_event)
    for x in xrange(10):
        event = client_channel.recv()
        assert list(event.args) == [x]


def test_events_channel_both_side():
    endpoint = random_ipc_endpoint()
    server_events = zerorpc.Events(zmq.ROUTER)
    server_events.bind(endpoint)
    server = zerorpc.ChannelMultiplexer(server_events)

    client_events = zerorpc.Events(zmq.DEALER)
    client_events.connect(endpoint)
    client = zerorpc.ChannelMultiplexer(client_events)

    client_channel = client.channel()
    client_channel.emit('openthat', (42,))

    event = server.recv()
    print event
    assert list(event.args) == [42]
    assert event.name == 'openthat'

    server_channel = server.channel(event)
    server_channel.emit('test', (21,))

    event = client_channel.recv()
    assert list(event.args) == [21]
    assert event.name == 'test'

    server_channel.emit('test', (22,))

    event = client_channel.recv()
    assert list(event.args) == [22]
    assert event.name == 'test'

    server_events.close()
    server_channel.close()
    client_channel.close()
    client_events.close()
