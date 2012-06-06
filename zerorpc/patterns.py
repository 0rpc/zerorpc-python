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



class ReqRep:

    def process_call(self, context, bufchan, event, functor):
        result = context.middleware_call_procedure(functor, *event.args)
        bufchan.emit('OK', (result,), context.middleware_get_task_context())

    def accept_answer(self, event):
        return True

    def process_answer(self, context, bufchan, event, method,
            raise_remote_error):
        result = event.args[0]
        if event.name == 'ERR':
            raise_remote_error(event)
        bufchan.close()
        return result


class ReqStream:

    def process_call(self, context, bufchan, event, functor):
        xheader = context.middleware_get_task_context()
        for result in iter(context.middleware_call_procedure(functor,
                *event.args)):
            bufchan.emit('STREAM', result, xheader)
        bufchan.emit('STREAM_DONE', None, xheader)

    def accept_answer(self, event):
        return event.name in ('STREAM', 'STREAM_DONE')

    def process_answer(self, context, bufchan, event, method,
            raise_remote_error):

        def is_stream_done(event):
            return event.name == 'STREAM_DONE'
        bufchan.on_close_if = is_stream_done

        def iterator(event):
            while event.name == 'STREAM':
                yield event.args
                event = bufchan.recv()
            if event.name == 'ERR':
                raise_remote_error(event)
            bufchan.close()

        return iterator(event)


patterns_list = [ReqStream(), ReqRep()]
