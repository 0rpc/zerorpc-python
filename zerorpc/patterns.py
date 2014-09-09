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

    def process_call(self, context, channel, req_event, functor):
        context.hook_server_before_exec(req_event)
        result = functor(*req_event.args)
        rep_event = channel.new_event('OK', (result,),
                context.hook_get_task_context())
        context.hook_server_after_exec(req_event, rep_event)
        channel.emit_event(rep_event)

    def accept_answer(self, event):
        return True

    def process_answer(self, context, channel, req_event, rep_event,
            handle_remote_error):
        if rep_event.name == 'ERR':
            exception = handle_remote_error(rep_event)
            context.hook_client_after_request(req_event, rep_event, exception)
            raise exception
        context.hook_client_after_request(req_event, rep_event)
        channel.close()
        result = rep_event.args[0]
        return result


class ReqStream:

    def process_call(self, context, channel, req_event, functor):
        context.hook_server_before_exec(req_event)
        xheader = context.hook_get_task_context()
        for result in iter(functor(*req_event.args)):
            channel.emit('STREAM', result, xheader)
        done_event = channel.new_event('STREAM_DONE', None, xheader)
        # NOTE: "We" made the choice to call the hook once the stream is done,
        # the other choice was to call it at each iteration. I don't think that
        # one choice is better than the other, so I'm fine with changing this
        # or adding the server_after_iteration and client_after_iteration hooks.
        context.hook_server_after_exec(req_event, done_event)
        channel.emit_event(done_event)

    def accept_answer(self, event):
        return event.name in ('STREAM', 'STREAM_DONE')

    def process_answer(self, context, channel, req_event, rep_event,
            handle_remote_error):

        def is_stream_done(rep_event):
            return rep_event.name == 'STREAM_DONE'
        channel.on_close_if = is_stream_done

        def iterator(req_event, rep_event):
            while rep_event.name == 'STREAM':
                # Like in process_call, we made the choice to call the
                # after_exec hook only when the stream is done.
                yield rep_event.args
                rep_event = channel.recv()
            if rep_event.name == 'ERR':
                exception = handle_remote_error(rep_event)
                context.hook_client_after_request(req_event, rep_event, exception)
                raise exception
            context.hook_client_after_request(req_event, rep_event)
            channel.close()

        return iterator(req_event, rep_event)


patterns_list = [ReqStream(), ReqRep()]
