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

import functools
import nose.exc
import random
import os

_tmpfiles = []

def random_ipc_endpoint():
    tmpfile = '/tmp/zerorpc_test_socket_{0}.sock'.format(
            str(random.random())[2:])
    _tmpfiles.append(tmpfile)
    return 'ipc://{0}'.format(tmpfile)

def teardown():
    global _tmpfiles
    for tmpfile in _tmpfiles:
        print 'unlink', tmpfile
        try:
            os.unlink(tmpfile)
        except Exception:
            pass
    _tmpfiles = []

def skip(reason):
    def _skip(test):
        @functools.wraps(test)
        def wrap():
            raise nose.exc.SkipTest(reason)
        return wrap
    return _skip
