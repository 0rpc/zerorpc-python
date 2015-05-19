# zerorpc Protocol

THIS DOCUMENT IS INCOMPLETE, WORK IN PROGRESS!

This document attempts to define the zerorpc protocol.

## Introduction & History

zerorpc features a dead-simple API for exposing any object or module over the
network, and a powerful gevent implementation which supports multiple ZMQ
socket types, streaming, heartbeats and more. It also includes a simple
command-line tool for interactive querying and introspection.

zerorpc uses ZMQ as a transport, but uses a communication protocol that is
transport-agnostic. For a long time the reference documentation for that
protocol was the python code itself. However since its recent surge in
popularity many people have expressed interest in porting it to other
programming languages. We hope that this standalone protocol documentation will
help them.

> The python implementation of zerorpc act as a reference for the whole
> protocol.  New features and experiments are implemented and tested in this
> version first.

[zerorpc](http://www.zerorpc.io) is a modern communication layer for
distributed systems built on top of [ZeroMQ](http://zeromq.org), initially
developed at [dotCloud](http://www.dotcloud.com) starting in 2010 and
open-sourced in 2012. when dotCloud pivoted to [Docker](http://www.docker.com),
dotCloud was acquired by [cloudControl](https://www.cloudcontrol.com/), which
then migrated over to theirs own PaaS before shutting it down.

In 2015, I (François-Xavier Bourlet) was given zerorpc by cloudControl, in an
attempt to revive the project, maintain it, and hopefully drive its
development.

### Warning

A short warning: zerorpc started as a simple tool to solve a simple problem. It
was progressively refined and improved to satisfy the growing needs of the
dotCloud platform. The emphasis is on practicality, robustness and operational
simplicity - sometimes at the expense of formal elegance and optimizations. We
will gladly welcome patches focused on the latter so long as they don't hurt
the former.


## Layers

Before diving into any details, let's divide zerorpc's protocol in three
different layers:

 1. Wire (or transport) layer; a combination of ZMQ <http://www.zeromq.org/>
    and msgpack <http://msgpack.org/>.
 2. Event (or message) layer; this is probably the most complex part, since
    it handles heartbeat, multiplexing, and events.
 3. RPC layer; that's where you can find the notion of request and response.

## Wire layer

The wire layer is a combination of ZMQ and msgpack.

The basics:

 - A zerorpc server can listen on as many ZMQ sockets as you like. Actually,
   a ZMQ socket can bind to multiple addresses. It can even *connect* to the
   clients (think about it as a worker connecting to a hub), but there are
   some limitations in that case (see below). zerorpc doesn't
   have to do anything specific for that: ZMQ handles it automatically.
 - A zerorpc client can connect to multiple zerorpc servers. However, it should
   create a new ZMQ socket for each connection.

Since zerorpc implements heartbeat and streaming, it expects a kind of
persistent, end-to-end, connection between the client and the server.
It means that we cannot use the load-balancing features built into ZMQ.
Otherwise, the various messages composing a single conversation could
end up in different places.

That's why there are limitations when the server connects to the client:
if there are multiple servers connecting to the same client, bad things
will happen.

> Note that the current implementation of zerorpc for Python doesn't implement
> its own load-balancing (yet), and still uses one ZMQ socket for connecting to
> many servers. You can still use ZMQ load-balancing if you accept to disable
> heartbeat and don't use streamed responses.

Every event from the event layer will be serialized with msgpack.


## Event layer

The event layer is the most complex of all three layers. The majority of the
code for the Python implementation deals with this layer.

This layer provides:

 - basic events;
 - multiplexed channels, allowing concurrency.


### Basic Events

An event is a tuple (or array in JSON), containing in the following order:

 1. the event's header -> dictionary (or object in JSON)
 2. the event's names -> string
 3. the event's arguments -> any kind of value; but in practice, for backward
    compatibility, it is recommended that this is a tuple (an empty one is OK).

All events headers must contain an unique message id and the protocol version:

	{
		"message_id": "6ce9503a-bfb8-486a-ac79-e2ed225ace79",
		"v": 3
	}

The message id should be unique for the lifetime of the connection between a
client and a server.

> It doesn't need to be an UUID, but again, for backward compatibility reasons,
> it is better if it follows the UUID format.

This document talks only about the version 3 of the protocol.

> The Python implementation has a lot of backward compatibility code, to handle
> communication between all three versions of the protocol.


### Multiplexed Channels

 - Each new event opens a new channel implicitly.
 - The id of the new event will represent the channel id for the connection.
 - Each consecutive event on a channel will have the header field "response_to"
   set to the channel id:

		{
			"message_id": "6ce9503a-bfb8-486a-ac79-e2ed225ace79",
			"response_to": "6636fb60-2bca-4ecb-8cb4-bbaaf174e9e6"
		}

#### Heartbeat

Each part of a channel must send a heartbeat at regular intervals.

The default heartbeat frequency is 5 seconds.

> Note that technically, the heartbeat could be sitting on the connection level
> instead of the channel level; but again, backward compatibility requires
> to run it per channel at this point.

The heartbeat is defined as follow:

 - Event's name: '\_zpc\_hb'
 - Event's args: null

When no heartbeat even is received after 2 heartbeat intervals (so, 10s by default),
we consider that the remote is lost.

> The Python implementation raises the LostRemote exception, and even
> manages to cancel a long-running task on a LostRemote. FIXME what does that mean?

#### Buffering (or congestion control) on channels

Both sides have a buffer for incoming messages on a channel. A peer can
send an advisory message to the other end of the channel, to inform it of the
size of its local buffer. This is a hint for the remote, to tell it "send me
more data!"

 - Event's name: '\_zpc\_more'
 - Event's args: integer representing how many entries are available in the client's buffer.

FIXME WIP

## RPC Layer

In the first version of zerorpc, this was the main (and only) layer.
Three kinds of events can occur at this layer: request (=function call),
response (=function return), error (=exception).

Request:

 - Event's name: string with the name of the method to call.
 - Event's args: tuple of arguments for the method.

Note: keyword arguments are not supported, because some languages don't
support them. If you absolutely want to call functions with keyword
arguments, you can use a wrapper; e.g. expose a function like
"call_with_kwargs(function_name, args, kwargs)", where args is a list,
and kwargs a dict. It might be an interesting idea to add such a
helper function into zerorpc default methods (see below for definitions
of existing default methods).

Response:

 - Event's name: string "OK"
 - Event's args: tuple containing the returned value

> Note that if the return value is a tuple, it is itself wrapped inside a
> tuple - again, for backward compatibility reasons.

FIXME - is [] equivalent to [null]?

If an error occurs (either at the transport level, or if an uncaught
exception is raised), we use the ERR event.

 - Event's name: string "ERR"
 - Event's args: tuple of 3 strings:
	- Name of the error (it should be the exception class name, or another
	  meaningful keyword).
	- Human representation of the error (preferably in english).
	- If possible a pretty printed traceback of the call stack when the error occured.

> A future version of the protocol will probably add a structured version of the
> traceback, allowing machine-to-machine stack walking and better cross-language
> exception representation.


### Default calls

When exposing some code with zerorpc, a number of methods/functions are
automatically added, to provide useful debugging and development tools.

 - \_zerorpc\_ping() just answers with a pong message.
 - \_zerorpc\_inspect() returns all the available calls, with their
   signature and documentation.

FIXME we should rather standardize about the basic introspection calls.


### Streaming

At the protocol level, streaming is straightforward. When a server wants
to stream some data, instead of sending a "OK" message, it sends a "STREAM"
message. The client will know that it needs to keep waiting for more.
At the end of the sream, a "STREAM_DONE" message is expected.

Formal definitions follow.

Messages part of a stream:

 - Event's name: string "STREAM"
 - Event's args: tuple containing the streamed value

When the STREAM reaches its end:

 - Event's name: string "STREAM\_DONE"
 - Event's args: null

> The Python implementation represents a stream by an iterator on both sides.
