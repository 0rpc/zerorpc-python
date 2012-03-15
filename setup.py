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

import zerorpc

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


import os
if os.environ.get('STATIC_DEPS', None) in ('1', 'true'):
    PYZMQ_PACKAGE = 'pyzmq-static>=2.1.7,<2.2'
else:
    PYZMQ_PACKAGE = 'pyzmq>=2.1.11,<2.2'


setup(
    name='zerorpc',
    version=zerorpc.__version__,
    description='zerorpc is a flexible RPC based on zeromq.',
    author=zerorpc.__author__,
    url='https://github.com/dotcloud/zerorpc-python',
    packages=['zerorpc'],
    install_requires=[
            'argparse',
            'gevent',
            'msgpack-python',
            PYZMQ_PACKAGE,
    ],
    zip_safe=False,
    scripts=[
            'bin/zerorpc-client'
        ],
    license='MIT',
    classifiers=(
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
    ),
)
