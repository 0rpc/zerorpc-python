# -*- coding: utf-8 -*-


import uuid

import gevent_zmq as zmq


class Context(zmq.Context):
    _instance = None

    def __init__(self):
        self._middlewares = []
        self._middlewares_hooks = {
                'resolve_endpoint': [],
                'raise_error': []
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
