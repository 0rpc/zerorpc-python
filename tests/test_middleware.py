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


def test_resolve_endpoint():
    test_endpoint = 'ipc://test_resolve_endpoint'
    c = zerorpc.Context()

    def resolve(endpoint):
        if endpoint == 'titi':
            return test_endpoint
        return endpoint

    cnt = c.register_middleware({
        'resolve_endpoint': resolve
        })
    print 'registered_count:', cnt
    assert cnt == 1

    print 'resolve titi:', c.middleware_resolve_endpoint('titi')
    assert c.middleware_resolve_endpoint('titi') == test_endpoint

    print 'resolve toto:', c.middleware_resolve_endpoint('toto')
    assert c.middleware_resolve_endpoint('toto') == 'toto'

    class Resolver():

        def resolve_endpoint(self, endpoint):
            if endpoint == 'toto':
                return test_endpoint
            return endpoint

    cnt = c.register_middleware(Resolver())
    print 'registered_count:', cnt
    assert cnt == 1

    print 'resolve titi:', c.middleware_resolve_endpoint('titi')
    assert c.middleware_resolve_endpoint('titi') == test_endpoint
    print 'resolve toto:', c.middleware_resolve_endpoint('toto')
    assert c.middleware_resolve_endpoint('toto') == test_endpoint

    c2 = zerorpc.Context()
    print 'resolve titi:', c2.middleware_resolve_endpoint('titi')
    assert c2.middleware_resolve_endpoint('titi') == 'titi'
    print 'resolve toto:', c2.middleware_resolve_endpoint('toto')
    assert c2.middleware_resolve_endpoint('toto') == 'toto'


def test_resolve_endpoint_events():
    test_endpoint = 'ipc://test_resolve_endpoint_events'
    c = zerorpc.Context()

    class Resolver():
        def resolve_endpoint(self, endpoint):
            if endpoint == 'some_service':
                return test_endpoint
            return endpoint

    class Srv(zerorpc.Server):
        def hello(self):
            print 'heee'
            return 'world'

    srv = Srv(heartbeat=1, context=c)
    with assert_raises(zmq.ZMQError):
        srv.bind('some_service')

    cnt = c.register_middleware(Resolver())
    assert cnt == 1
    srv.bind('some_service')
    gevent.spawn(srv.run)

    client = zerorpc.Client(heartbeat=1, context=c)
    client.connect('some_service')
    assert client.hello() == 'world'

    client.close()
    srv.close()


def test_raise_error():
    endpoint = 'ipc://test_raise_error'
    c = zerorpc.Context()

    class DummyRaiser():
        def raise_error(self, event):
            pass

    class Srv(zerorpc.Server):
        pass

    srv = Srv(context=c)
    srv.bind(endpoint)
    gevent.spawn(srv.run)

    client = zerorpc.Client(context=c)
    client.connect(endpoint)

    with assert_raises(zerorpc.RemoteError):
        client.donotexist()

    cnt = c.register_middleware(DummyRaiser())
    assert cnt == 1

    with assert_raises(zerorpc.RemoteError):
        client.donotexist()

    class HorribleEvalRaiser():
        def raise_error(self, event):
            (name, msg, tb) = event.args
            etype = eval(name)
            e = etype(tb)
            raise e

    cnt = c.register_middleware(HorribleEvalRaiser())
    assert cnt == 1

    with assert_raises(NameError):
        try:
            client.donotexist()
        except NameError as e:
            print 'got it:', e
            raise

    client.close()
    srv.close()
