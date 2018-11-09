# -*- coding: utf-8 -*-
from importlib import import_module

__author__ = 'nemo'

class Singleton(type):
    def __init__(cls, name, bases, dict):
        super(Singleton, cls).__init__(name, bases, dict)
        cls.instance = None

    def __call__(cls, *args, **kw):
        if cls.instance is None:
            cls.instance = super(Singleton, cls).__call__(*args, **kw)
        return cls.instance


def get_mod_func(path):
    try:
        dot = path.rindex(':')
    except ValueError:
        try:
            dot = path.rindex('.')
        except ValueError:
            return path, ''

    return path[:dot], path[dot+1:]

def load_by_path(path):
    mod_name, func_name = get_mod_func(path)
    if func_name != '':
        package = None
        if path.startswith('.'):
            package = __package__

        return getattr(import_module(mod_name, package), func_name)