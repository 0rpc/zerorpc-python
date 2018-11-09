# coding=utf-8
import pickle

__author__ = 'nemo'


class Serializer(object):

    def pack(self, data):
        return pickle.dumps(data)

    def unpack(self, blob):
        return pickle.loads(blob)
