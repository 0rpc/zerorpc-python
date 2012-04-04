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


import uuid
import functools

import gevent_zmq as zmq


class Context(zmq.Context):
    _instance = None

    def __init__(self):
        self._middlewares = []
        self._middlewares_hooks = {
                'resolve_endpoint': [],
                'raise_error': [],
                'call_procedure': [],
                'load_task_context': [],
                'get_task_context': [],
                }

    @staticmethod
    def get_instance():
        if Context._instance is None:
            Context._instance = Context()
        return Context._instance

    def new_msgid(self):
        return str(uuid.uuid4())

    def register_middleware(self, middleware_instance):
        registered_count = 0
        self._middlewares.append(middleware_instance)
        for hook in self._middlewares_hooks.keys():
            functor = getattr(middleware_instance, hook, None)
            if functor is None:
                try:
                    functor = middleware_instance.get(hook, None)
                except AttributeError:
                    pass
            if functor is not None:
                self._middlewares_hooks[hook].append(functor)
                registered_count += 1
        return registered_count

    def middleware_resolve_endpoint(self, endpoint):
        for functor in self._middlewares_hooks['resolve_endpoint']:
            endpoint = functor(endpoint)
        return endpoint

    def middleware_raise_error(self, event):
        for functor in self._middlewares_hooks['raise_error']:
            functor(event)

    def middleware_call_procedure(self, procedure, *args, **kwargs):
        class chain(object):
            def __init__(self, fct, next):
                functools.update_wrapper(self, next)
                self.fct = fct
                self.next = next

            def __call__(self, *args, **kwargs):
                return self.fct(self.next, *args, **kwargs)

        for functor in self._middlewares_hooks['call_procedure']:
            procedure = chain(functor, procedure)
        return procedure(*args, **kwargs)

    def middleware_load_task_context(self, event_header):
        for functor in self._middlewares_hooks['load_task_context']:
            functor(event_header)

    def middleware_get_task_context(self):
        event_header = {}
        for functor in self._middlewares_hooks['get_task_context']:
            event_header.update(functor())
        return event_header
