# -*- coding: utf-8 -*-


import zerorpc

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


setup(
    name         = 'zerorpc',
    version      = zerorpc.__version__,
    description  = 'zerorpc is a flexible RPC based on zeromq.',
    author       = zerorpc.__author__,
    url          = 'https://github.com/dotcloud/zerorpc-python',
    packages     = ['zerorpc'],
    install_requires = [
            'argparse',
            'gevent',
            'msgpack-python',
            'pyzmq-static==2.1.7',
    ],
    zip_safe     = False,
    scripts      = [
            'bin/zerorpc-client'
        ],
    license      = 'MIT',
    classifiers=(
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
    ),
)
