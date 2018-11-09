from zerorpc.serializers.default import Serializer as M
from zerorpc.serializers.pickle import Serializer as P
from zerorpc.serializers.msgpack_numpy import Serializer as N

import numpy as np

from .testutils import teardown, random_ipc_endpoint, TIME_FACTOR


def test_msgpack():
    x = (1, 2, 3)
    ser = M()
    blob = ser.pack(x)
    print(ser.unpack(blob))
    assert x == ser.unpack(blob)


def test_pickle():
    x = (1, 2, 3)
    ser = P()
    blob = ser.pack(x)
    assert x == ser.unpack(blob)


def test_msgpack_numpy():
    ser = N()
    x = (1, 2, 3)
    blob = ser.pack(x)
    xu = ser.unpack(blob)
    assert type(xu) == type(x)
    assert xu == x

    ser = N()
    x = np.array((1, 2, 3))
    print(x)
    blob = ser.pack(x)
    xu = ser.unpack(blob)
    print(xu)
    assert type(xu) == type(x)
    assert xu.dtype == x.dtype
