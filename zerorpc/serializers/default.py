# coding=utf-8
import msgpack


class Serializer(object):

    def pack(self, data):
        return msgpack.Packer(use_bin_type=True).pack(data)

    def unpack(self, blob):
        unpacker = msgpack.Unpacker(raw=False)
        unpacker.feed(blob)
        return unpacker.unpack()
