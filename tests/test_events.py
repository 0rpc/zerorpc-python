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

class MokupContext():
    _next_id = 0

    def new_msgid(self):
        new_id = MokupContext._next_id
        MokupContext._next_id += 1
        return new_id


def test_context():
    c = zerorpc.Context()
    assert c.new_msgid() is not None


def test_event():
    context = MokupContext()
    event = zerorpc.Event('mylittleevent', (None,), context=context)
    print event
    assert event.name == 'mylittleevent'
    assert event.header['message_id'] == 0
    assert event.args == (None,)

    event = zerorpc.Event('mylittleevent2', ('42',), context=context)
    print event
    assert event.name == 'mylittleevent2'
    assert event.header['message_id'] == 1
    assert event.args == ('42',)

    event = zerorpc.Event('mylittleevent3', ('a', 42), context=context)
    print event
    assert event.name == 'mylittleevent3'
    assert event.header['message_id'] == 2
    assert event.args == ('a', 42)

    event = zerorpc.Event('mylittleevent4', ('b', 21), context=context)
    print event
    assert event.name == 'mylittleevent4'
    assert event.header['message_id'] == 3
    assert event.args == ('b', 21)

    packed = event.pack()
    unpacked = zerorpc.Event.unpack(packed)
    print unpacked

    assert unpacked.name == 'mylittleevent4'
    assert unpacked.header['message_id'] == 3
    assert list(unpacked.args) == ['b', 21]

    event = zerorpc.Event('mylittleevent5', ('c', 24, True),
            header={'lol': 'rofl'}, context=None)
    print event
    assert event.name == 'mylittleevent5'
    assert event.header['lol'] == 'rofl'
    assert event.args == ('c', 24, True)

    event = zerorpc.Event('mod', (42,), context=context)
    print event
    assert event.name == 'mod'
    assert event.header['message_id'] == 4
    assert event.args == (42,)
    event.header.update({'stream': True})
    assert event.header['stream'] is True


def test_events_req_rep():
    endpoint = random_ipc_endpoint()
    server = zerorpc.Events(zmq.REP)
    server.bind(endpoint)

    client = zerorpc.Events(zmq.REQ)
    client.connect(endpoint)

    client.emit('myevent', ('arg1',))

    event = server.recv()
    print event
    assert event.name == 'myevent'
    assert list(event.args) == ['arg1']


def test_events_req_rep2():
    endpoint = random_ipc_endpoint()
    server = zerorpc.Events(zmq.REP)
    server.bind(endpoint)

    client = zerorpc.Events(zmq.REQ)
    client.connect(endpoint)

    for i in xrange(10):
        client.emit('myevent' + str(i), (i,))
        event = server.recv()
        print event
        assert event.name == 'myevent' + str(i)
        assert list(event.args) == [i]

        server.emit('answser' + str(i * 2), (i * 2,))
        event = client.recv()
        print event
        assert event.name == 'answser' + str(i * 2)
        assert list(event.args) == [i * 2]


def test_events_dealer_router():
    endpoint = random_ipc_endpoint()
    server = zerorpc.Events(zmq.ROUTER)
    server.bind(endpoint)

    client = zerorpc.Events(zmq.DEALER)
    client.connect(endpoint)

    for i in xrange(6):
        client.emit('myevent' + str(i), (i,))
        event = server.recv()
        print event
        assert event.name == 'myevent' + str(i)
        assert list(event.args) == [i]

        reply_event = server.new_event('answser' + str(i * 2), (i * 2,))
        reply_event.identity = event.identity
        server.emit_event(reply_event)
        event = client.recv()
        print event
        assert event.name == 'answser' + str(i * 2)
        assert list(event.args) == [i * 2]


def test_events_push_pull():
    endpoint = random_ipc_endpoint()
    server = zerorpc.Events(zmq.PULL)
    server.bind(endpoint)

    client = zerorpc.Events(zmq.PUSH)
    client.connect(endpoint)

    for x in xrange(10):
        client.emit('myevent', (x,))

    for x in xrange(10):
        event = server.recv()
        print event
        assert event.name == 'myevent'
        assert list(event.args) == [x]
