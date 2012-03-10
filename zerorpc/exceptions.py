# -*- coding: utf-8 -*-


class LostRemote(Exception):
    pass


class TimeoutExpired(Exception):

    def __init__(self, timeout_s, when=None):
        msg = 'timeout after {0}s'
        if when:
            msg = '{0}, when {1}'.format(msg, when)
        super(TimeoutExpired, self).__init__(msg)


class RemoteError(Exception):

    def __init__(self, name, human_msg, human_traceback):
        self.name = name
        self.msg = human_msg
        self.traceback = human_traceback

    def __str__(self):
        if self.traceback is not None:
            return self.traceback
        return '{0}: {1}'.format(self.name, self.msg)
