# -*- coding: utf-8 -*-
# Open Source Initiative OSI - The MIT License (MIT):Licensing
#
# The MIT License (MIT)
# Copyright (c) 2015 François-Xavier Bourlet (bombela+zerorpc@gmail.com)
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

import sys

if sys.version_info < (3, 0):
    execfile('zerorpc/version.py')
else:
    exec(compile(open('zerorpc/version.py', encoding='utf8').read(), 'zerorpc/version.py', 'exec'))

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


requirements = [
    'msgpack-python>=0.4.0',
    'pyzmq>=13.1.0',
    'future',
]

if sys.version_info < (2, 7):
    requirements.append('argparse')

if sys.version_info < (3, 0):
    requirements.append('gevent>=1.0')
else:
    requirements.append('gevent>=1.1rc5')


setup(
    name='zerorpc',
    version=__version__,
    description='zerorpc is a flexible RPC based on zeromq.',
    author=__author__,
    url='https://github.com/0rpc/zerorpc-python',
    packages=['zerorpc'],
    install_requires=requirements,
    tests_require=['nose'],
    test_suite='nose.collector',
    zip_safe=False,
    entry_points={'console_scripts': ['zerorpc = zerorpc.cli:main']},
    license='MIT',
    classifiers=(
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
    ),
)
