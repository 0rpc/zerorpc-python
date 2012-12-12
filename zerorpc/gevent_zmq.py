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
#
# Based on https://github.com/traviscline/gevent-zeromq/

# We want to act like zmq
from zmq import *

# A way to access original zmq
import zmq as _zmq

import gevent.event
import gevent.core
import sys

class Context(_zmq.Context):

    def socket(self, socket_type):
        if self.closed:
            raise _zmq.ZMQError(_zmq.ENOTSUP)
        return Socket(self, socket_type)


class Socket(_zmq.Socket):

    def __init__(self, context, socket_type):
        super(Socket, self).__init__(context, socket_type)
        on_state_changed_fd = self.getsockopt(_zmq.FD)
        self._readable = gevent.event.Event()
        self._writable = gevent.event.Event()
        try:
            # gevent>=1.0
            self._state_event = gevent.hub.get_hub().loop.io(
                on_state_changed_fd, gevent.core.READ)
            self._state_event.start(self._on_state_changed)
        except AttributeError:
            # gevent<1.0
            self._state_event = gevent.core.read_event(on_state_changed_fd,
                    self._on_state_changed, persist=True)

    def _on_state_changed(self, event=None, _evtype=None):
        if self.closed:
            self._writable.set()
            self._readable.set()
            return

        events = self.getsockopt(_zmq.EVENTS)
        if events & _zmq.POLLOUT:
            self._writable.set()
        if events & _zmq.POLLIN:
            self._readable.set()

    def close(self):
        if not self.closed and getattr(self, '_state_event', None):
            try:
                # gevent>=1.0
                self._state_event.stop()
            except AttributeError:
                # gevent<1.0
                self._state_event.cancel()
        super(Socket, self).close()

    def send(self, data, flags=0, copy=True, track=False):
        if flags & _zmq.NOBLOCK:
            return super(Socket, self).send(data, flags, copy, track)
        flags |= _zmq.NOBLOCK
        while True:
            try:
                msg = super(Socket, self).send(data, flags, copy, track)
                # The following call, force polling the state of the zmq socket
                # (POLLIN and/or POLLOUT). It seems that a POLLIN event is often
                # missed when the socket is used to send at the same time,
                # forcing to poll at this exact moment seems to reduce the
                # latencies when a POLLIN event is missed. The drawback is a
                # reduced throughput (roughly 8.3%) in exchange of a normal
                # concurrency. In other hand, without the following line, you
                # loose 90% of the performances as soon as there is simultaneous
                # send and recv on the socket.
                self._on_state_changed()
                return msg
            except _zmq.ZMQError, e:
                if e.errno != _zmq.EAGAIN:
                    raise
            self._writable.clear()
            # The following sleep(0) force gevent to switch out to another
            # coroutine and seems to refresh the notion of time that gevent may
            # have. This definitively eliminate the gevent bug that can trigger
            # a timeout too soon under heavy load. In theory it will incur more
            # CPU usage, but in practice it balance even with the extra CPU used
            # when the timeout triggers too soon in the following loop. So for
            # the same CPU load, you get a better throughput (roughly 18.75%).
            gevent.sleep(0)
            while not self._writable.wait(timeout=1):
                if self.getsockopt(_zmq.EVENTS) & _zmq.POLLOUT:
                    print>>sys.stderr, "/!\\ gevent_zeromq BUG /!\\ " \
                        "catching up after missing event (SEND) /!\\"
                    break

    def recv(self, flags=0, copy=True, track=False):
        if flags & _zmq.NOBLOCK:
            return super(Socket, self).recv(flags, copy, track)
        flags |= _zmq.NOBLOCK
        while True:
            try:
                msg = super(Socket, self).recv(flags, copy, track)
                # The following call, force polling the state of the zmq socket
                # (POLLIN and/or POLLOUT). It seems that a POLLOUT event is
                # often missed when the socket is used to receive at the same
                # time, forcing to poll at this exact moment seems to reduce the
                # latencies when a POLLOUT event is missed. The drawback is a
                # reduced throughput (roughly 8.3%) in exchange of a normal
                # concurrency. In other hand, without the following line, you
                # loose 90% of the performances as soon as there is simultaneous
                # send and recv on the socket.
                self._on_state_changed()
                return msg
            except _zmq.ZMQError, e:
                if e.errno != _zmq.EAGAIN:
                    raise
            self._readable.clear()
            # The following sleep(0) force gevent to switch out to another
            # coroutine and seems to refresh the notion of time that gevent may
            # have. This definitively eliminate the gevent bug that can trigger
            # a timeout too soon under heavy load. In theory it will incur more
            # CPU usage, but in practice it balance even with the extra CPU used
            # when the timeout triggers too soon in the following loop. So for
            # the same CPU load, you get a better throughput (roughly 18.75%).
            gevent.sleep(0)
            while not self._readable.wait(timeout=1):
                if self.getsockopt(_zmq.EVENTS) & _zmq.POLLIN:
                    print>>sys.stderr, "/!\\ gevent_zeromq BUG /!\\ " \
                        "catching up after missing event (RECV) /!\\"
                    break
