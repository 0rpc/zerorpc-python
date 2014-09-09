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

# execfile() doesn't exist in Python 3, this way we are compatible with both.
exec(compile(open('zerorpc/version.py').read(), 'zerorpc/version.py', 'exec'))

import sys


try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


requirements = [
    'gevent>=1.0',
    'msgpack-python',
    'pyzmq>=13.1.0'
]
if sys.version_info < (2, 7):
    requirements.append('argparse')


setup(
    name='zerorpc',
    version=__version__,
    description='zerorpc is a flexible RPC based on zeromq.',
    author=__author__,
    url='https://github.com/dotcloud/zerorpc-python',
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
    ),
)
