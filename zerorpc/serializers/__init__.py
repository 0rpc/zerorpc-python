# coding=utf-8
__author__ = 'nemo'


class BaseSerializer(object):

    def pack(self, data):
        raise NotImplemented

    def unpack(self, blob):
        raise NotImplemented
