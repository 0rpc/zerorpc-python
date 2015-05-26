#!/usr/bin/env python
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


import argparse
import json
import sys
import inspect
import os
import logging
from pprint import pprint

import zerorpc


parser = argparse.ArgumentParser(
    description='Make a zerorpc call to a remote service.'
)

client_or_server = parser.add_mutually_exclusive_group()
client_or_server.add_argument('--client', action='store_true', default=True,
        help='remote procedure call mode (default)')
client_or_server.add_argument('--server', action='store_false', dest='client',
        help='turn a given python module into a server')

parser.add_argument('--connect', action='append', metavar='address',
                    help='specify address to connect to. Can be specified \
                    multiple times and in conjunction with --bind')
parser.add_argument('--bind', action='append', metavar='address',
                    help='specify address to listen to. Can be specified \
                    multiple times and in conjunction with --connect')
parser.add_argument('--timeout', default=30, metavar='seconds', type=int,
                    help='abort request after X seconds. \
                    (default: 30s, --client only)')
parser.add_argument('--heartbeat', default=5, metavar='seconds', type=int,
                    help='heartbeat frequency. You should always use \
                    the same frequency as the server. (default: 5s)')
parser.add_argument('-j', '--json', default=False, action='store_true',
                    help='arguments are in JSON format and will be be parsed \
                    before being sent to the remote')
parser.add_argument('-pj', '--print-json', default=False, action='store_true',
                    help='print result in JSON format.')
parser.add_argument('-?', '--inspect', default=False, action='store_true',
                    help='retrieve detailed informations for the given \
                    remote (cf: command) method. If not method, display \
                    a list of remote methods signature. (only for --client).')
parser.add_argument('--active-hb', default=False, action='store_true',
                    help='enable active heartbeat. The default is to \
                    wait for the server to send the first heartbeat')
parser.add_argument('-d', '--debug', default=False, action='store_true',
                    help='Print zerorpc debug msgs, \
                    like outgoing and incomming messages.')
parser.add_argument('address', nargs='?', help='address to connect to. Skip \
                    this if you specified --connect or --bind at least once')
parser.add_argument('command', nargs='?',
                    help='remote procedure to call if --client (default) or \
                    python module/class to load if --server. If no command is \
                    specified, a list of remote methods are displayed.')
parser.add_argument('params', nargs='*',
                    help='parameters for the remote call if --client \
                    (default)')


def setup_links(args, socket):
    if args.bind:
        for endpoint in args.bind:
            print 'binding to "{0}"'.format(endpoint)
            socket.bind(endpoint)
    addresses = []
    if args.address:
        addresses.append(args.address)
    if args.connect:
        addresses.extend(args.connect)
    for endpoint in addresses:
        print 'connecting to "{0}"'.format(endpoint)
        socket.connect(endpoint)


def run_server(args):
    server_obj_path = args.command

    sys.path.insert(0, os.getcwd())
    if '.' in server_obj_path:
        modulepath, objname = server_obj_path.rsplit('.', 1)
        module = __import__(modulepath, fromlist=[objname])
        server_obj = getattr(module, objname)
    else:
        server_obj = __import__(server_obj_path)

    if callable(server_obj):
        server_obj = server_obj()

    server = zerorpc.Server(server_obj, heartbeat=args.heartbeat)
    if args.debug:
        server.debug = True
    setup_links(args, server)
    print 'serving "{0}"'.format(server_obj_path)
    return server.run()


# this function does a really intricate job to keep backward compatibility
# with a previous version of zerorpc, and lazily retrieving results if possible
def zerorpc_inspect_legacy(client, filter_method, long_doc, include_argspec):
    if filter_method is None:
        remote_methods = client._zerorpc_list()
    else:
        remote_methods = [filter_method]

    def remote_detailled_methods():
        for name in remote_methods:
            if include_argspec:
                argspec = client._zerorpc_args(name)
            else:
                argspec = None
            docstring = client._zerorpc_help(name)
            if docstring and not long_doc:
                docstring = docstring.split('\n', 1)[0]
            yield (name, argspec, docstring if docstring else '<undocumented>')

    if not include_argspec:
        longest_name_len = max(len(name) for name in remote_methods)
        return (longest_name_len, ((name, doc) for name, argspec, doc in
            remote_detailled_methods()))

    r = [(name + (inspect.formatargspec(*argspec)
                  if argspec else '(...)'), doc)
         for name, argspec, doc in remote_detailled_methods()]
    longest_name_len = max(len(name) for name, doc in r) if r else 0
    return (longest_name_len, r)


# handle the 'python formatted' _zerorpc_inspect, that return the output of
# "getargspec" from the python lib "inspect". A monstruosity from protocol v2.
def zerorpc_inspect_python_argspecs(remote_methods, filter_method, long_doc, include_argspec):
    def format_method(name, argspec, doc):
        if include_argspec:
            name += (inspect.formatargspec(*argspec) if argspec else
                '(...)')
        if not doc:
            doc = '<undocumented>'
        elif not long_doc:
            doc = doc.splitlines()[0]
        return (name, doc)
    r = [format_method(*methods_info) for methods_info in remote_methods if
         filter_method is None or methods_info[0] == filter_method]
    if not r:
        return None
    longest_name_len = max(len(name) for name, doc in r) if r else 0
    return (longest_name_len, r)


# Handles generically formatted arguments (not tied to any specific programming language).
def zerorpc_inspect_generic(remote_methods, filter_method, long_doc, include_argspec):
    def format_method(name, args, doc):
        if include_argspec:
            def format_arg(arg):
                def_val = arg.get('default')
                if def_val is None:
                    return arg['name']
                return '{0}={1}'.format(arg['name'], def_val)

            if args:
                name += '({0})'.format(', '.join(map(format_arg, args)))
            else:
                name += '(??)'

        if not doc:
            doc = '<undocumented>'
        elif not long_doc:
            doc = doc.splitlines()[0]
        return (name, doc)

    methods = [format_method(name, details['args'], details['doc'])
            for name, details in remote_methods.items()
            if filter_method is None or name == filter_method]

    longest_name_len = (max(len(name) for name, doc in methods)
            if methods else 0)
    return (longest_name_len, methods)


def zerorpc_inspect(client, method=None, long_doc=True, include_argspec=True):
    try:
        inspect_result = client._zerorpc_inspect()
        remote_methods = inspect_result['methods']
        legacy = False
    except (zerorpc.RemoteError, NameError):
        legacy = True

    if legacy:
        try:
            service_name = client._zerorpc_name()
        except (zerorpc.RemoteError):
            service_name = 'N/A'

        (longest_name_len, detailled_methods) = zerorpc_inspect_legacy(client,
                method, long_doc, include_argspec)
    else:
        service_name = inspect_result.get('name', 'N/A')
        if not isinstance(remote_methods, dict):
            (longest_name_len,
                detailled_methods) = zerorpc_inspect_python_argspecs(
                    remote_methods, method, long_doc, include_argspec)

        (longest_name_len, detailled_methods) = zerorpc_inspect_generic(
            remote_methods, method, long_doc, include_argspec)

    return longest_name_len, detailled_methods, service_name


def run_client(args):
    client = zerorpc.Client(timeout=args.timeout, heartbeat=args.heartbeat,
            passive_heartbeat=not args.active_hb)
    if args.debug:
        client.debug = True
    setup_links(args, client)
    if not args.command:
        (longest_name_len, detailled_methods, service) = zerorpc_inspect(client,
                long_doc=False, include_argspec=args.inspect)
        print '[{0}]'.format(service)
        if args.inspect:
            for (name, doc) in detailled_methods:
                print name
        else:
            for (name, doc) in detailled_methods:
                print '{0} {1}'.format(name.ljust(longest_name_len), doc)
        return
    if args.inspect:
        (longest_name_len, detailled_methods, service) = zerorpc_inspect(client,
                method=args.command)
        if detailled_methods:
            (name, doc) = detailled_methods[0]
            print '[{0}]\n{1}\n\n{2}\n'.format(service, name, doc)
        else:
            print '[{0}]\nNo documentation for "{1}".'.format(service, args.command)
        return
    if args.json:
        call_args = [json.loads(x) for x in args.params]
    else:
        call_args = args.params
    results = client(args.command, *call_args)
    if getattr(results, 'next', None) is None:
        if args.print_json:
            json.dump(results, sys.stdout)
        else:
            pprint(results)
    else:
        # streaming responses
        if args.print_json:
            first = True
            sys.stdout.write('[')
            for result in results:
                if first:
                    first = False
                else:
                    sys.stdout.write(',')
                json.dump(result, sys.stdout)
            sys.stdout.write(']')
        else:
            for result in results:
                pprint(result)


def main():
    logging.basicConfig()
    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.bind or args.connect:
        if args.command:
            args.params.insert(0, args.command)
        args.command = args.address
        args.address = None

    if not (args.bind or args.connect or args.address):
        parser.print_help()
        return -1

    if args.client:
        return run_client(args)

    if not args.command:
        parser.print_help()
        return -1

    return run_server(args)
