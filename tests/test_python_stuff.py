from datetime import datetime
from zerorpc import Context
from itertools import cycle
import numpy as np

import gevent
import zerorpc
from .testutils import random_ipc_endpoint


def test_pickle_tuple():

    class Srv(object):
        def echo(self, *args):
            return args

    endpoint = random_ipc_endpoint()

    context = Context()
    context.register_serializer("pickle")

    module = Srv()
    server = zerorpc.Server(module, context=context)
    server.bind(endpoint)
    gevent.spawn(server.run)

    client = zerorpc.Client(context=context)
    client.connect(endpoint)

    args = (1, 2, 3)
    res = client.echo(*args)
    assert len(res) == 3
    assert res == args

    client.close()
    server.close()


def test_pickle_cycle():

    class Srv(object):
        def echo(self, *args):
            return args

    endpoint = random_ipc_endpoint()

    context = Context()
    context.register_serializer("pickle")

    module = Srv()
    server = zerorpc.Server(module, context=context)
    server.bind(endpoint)
    gevent.spawn(server.run)

    client = zerorpc.Client(context=context)
    client.connect(endpoint)

    args = cycle((1, 2, 3))
    res = client.echo(args)[0]
    assert isinstance(res, cycle)
    # assert res == args

    client.close()
    server.close()


def test_pickle_numpy():

    class Srv(object):
        def echo(self, *args):
            return args

    endpoint = random_ipc_endpoint()

    context = Context()
    context.register_serializer("pickle")

    module = Srv()
    server = zerorpc.Server(module, context=context)
    server.bind(endpoint)
    gevent.spawn(server.run)

    client = zerorpc.Client(context=context)
    client.connect(endpoint)

    args = np.zeros((10, 10), dtype=np.float32)
    res = client.echo(args)[0]
    assert isinstance(res, np.ndarray)
    assert res.dtype == np.float32

    client.close()
    server.close()


def test_msgpack_numpy():

    class Srv(object):
        def echo(self, args):
            return args

    endpoint = random_ipc_endpoint()

    context = Context()
    context.register_serializer("msgpack_numpy")

    module = Srv()
    server = zerorpc.Server(module, context=context)
    server.bind(endpoint)
    gevent.spawn(server.run)

    client = zerorpc.Client(context=context)
    client.connect(endpoint)

    arg = np.arange(10)
    res = client.echo(arg)
    print(res)
    assert isinstance(res, np.ndarray)
    assert res.dtype == arg.dtype

    client.close()
    server.close()


def test_kwargs_pickle():

    class Srv(object):
        def echo(self, *args, **kwargs):
            return args, kwargs

    endpoint = random_ipc_endpoint()

    context = Context()
    context.register_serializer("pickle")

    module = Srv()
    server = zerorpc.Server(module, context=context)
    server.bind(endpoint)
    gevent.spawn(server.run)

    client = zerorpc.Client(context=context)
    client.connect(endpoint)

    args = 1, 2, 3
    kwargs = {'a': 7, 'b': 8, 'now': datetime.now()}
    res = client.echo(*args, **kwargs)
    assert len(res) == 2
    assert res[0] == args
    assert len(res[1]) == len(kwargs)
    assert 'a' in res[1] and 'b' in res[1] and isinstance(res[1]['now'], datetime)

    client.close()
    server.close()


def test_kwargs_msgpack():

    class Srv(object):
        def echo(self, *args, **kwargs):
            return args, kwargs

    endpoint = random_ipc_endpoint()

    context = Context()

    module = Srv()
    server = zerorpc.Server(module, context=context)
    server.bind(endpoint)
    gevent.spawn(server.run)

    client = zerorpc.Client(context=context)
    client.connect(endpoint)

    args = 1, 2, 3
    kwargs = {'a': 7, 'b': 8}
    res = client.echo(*args, **kwargs)
    assert len(res) == 2
    assert res[0] == args
    assert len(res[1]) == len(kwargs)
    assert 'a' in res[1] and 'b' in res[1]

    client.close()
    server.close()


def test_kwargs_msgpack_numpy():

    class Srv(object):
        def echo(self, *args, **kwargs):
            return args, kwargs

    endpoint = random_ipc_endpoint()

    context = Context()
    context.register_serializer("msgpack_numpy")

    module = Srv()
    server = zerorpc.Server(module, context=context)
    server.bind(endpoint)
    gevent.spawn(server.run)

    client = zerorpc.Client(context=context)
    client.connect(endpoint)

    args = 1, 2, 3
    kwargs = {'a': 7, 'b': 8}
    res = client.echo(*args, **kwargs)
    assert len(res) == 2
    assert res[0] == args
    assert len(res[1]) == len(kwargs)
    assert 'a' in res[1] and 'b' in res[1]

    client.close()
    server.close()
