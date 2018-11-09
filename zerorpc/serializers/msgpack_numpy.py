# coding=utf-8
import msgpack
import msgpack_numpy as m
m.patch()


class Serializer(object):

    def pack(self, data):
        r = msgpack.Packer(use_bin_type=True).pack(data)
        return r

    def unpack(self, blob):
        unpacker = msgpack.Unpacker(raw=False)
        unpacker.feed(blob)
        unpacked_msg = unpacker.unpack()
        return unpacked_msg
