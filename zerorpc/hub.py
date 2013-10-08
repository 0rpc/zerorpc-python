#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Open Source Initiative OSI - The MIT License (MIT):Licensing
#
# The MIT License (MIT)

import argparse
import zmq.green as zmq

parser = argparse.ArgumentParser(
    description='Run a zerorpc message hub.'
)

parser.add_argument('-c', '--client', action='append', metavar='client',
                    help='specify address to listen for client requests. \
                    Can be specified multiple times')
parser.add_argument('-s', '--server', action='append', metavar='server',
                    help='specify address to listen for server requests. \
                    Can be specified multiple times')


def run_hub(args):
    context = zmq.Context()
    router = context.socket(zmq.ROUTER)

    for client in args.client:
        router.bind(client)

    dealer = context.socket(zmq.DEALER)
    for server in args.server:
        dealer.bind(server)

    return zmq.device(zmq.QUEUE, router, dealer)


def main():
    args = parser.parse_args()

    if not args.client or not args.server:
        parser.print_help()
        return -1

    return run_hub(args)
