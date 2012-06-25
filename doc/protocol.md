# ZeroRPC Protocol

THIS DOCUMENT IS INCOMPLETE, WORK IN PROGRESS!

This document attempt to define zerorpc's protocol. We will see how the protocol
can be divided in different layers.

Note that many part of the protocol are either not elegant, could be more
efficient, or just "curious". This is because zerorpc started as a little tool
to solve a little problem. Before anybody knew, it was the core of all
inter-services communications at dotCloud (<http://www.dotcloud.com>).

Keep in mind that ZeroRPC keeps evolving, as we use it to solve new problems
everyday. There is no doubt that all discrepancy in the protocol will
disappear (slowly) over time, but backward compatibly is a bitch ;) 

> The python implementation of zerorpc act as a reference for the whole
> protocol.  New features and experiments are implemented and tested in this
> version first.  This is also this implementation that is powering dotCloud's
> infrastructure.

Before diving into any details, let's divide ZeroRPC's protocol in three
different layers:

 - wire (or transport) layer, a combination of ZMQ <http://www.zeromq.org/>
   and msgpack <http://msgpack.org/>.
 - event (or message) layer, the complex part handling heartbeat, multiplexing
   and the notion of events. 
 - "RPC" layer, where you can find the notion of request/response for example.

## Wire layer

The wire layer is a combination of ZMQ and msgpack.

Here's the basics:

 - A zerorpc Server can listen on many ZMQ socket as wished.
 - A zerorpc Client can connect on many zerorpc Server as needed, but should
   create a new ZMQ socket for each connection. It is assumed that every servers
   share the same API.  

Because zerorpc make use of heartbeat and other streaming-like features, all of
that multiplexed on top of one ZMQ socket, we can't use any of the
load-balancing features of ZMQ (ZMQ let choose between round-robin balancing or
routing, but not both). It also mean that a zerorpc Client can't listen either,
it need to connect to the server, not the opposite (but really, it shouldn't
affect you too much).

In short: Each connection from one zerorpc Client require its own ZMQ socket.

> Note that the current implementation of zerorpc for python doesn't implement
> its own load-balancing (yet), and still use one ZMQ socket for connecting to
> many servers. You can still use ZMQ load-balancing if you accept to disable
> heartbeat and forget using any streaming responses.

Every event from the event layer will be serialized with msgpack. 

## Event layer

The event layer is the most complex of all three layers. (And it is where lie
the majority of the code for the python implementation).

This layer provide:

 - The basics events mechanics.
 - A multiplexed channels system, to allow concurrency.

### Event mechanics

An event is a tuple (or array in json), containing in the following order:

 1. the event's header -> dictionary (or object in json)
 2. the event's names -> string
 3. the event's arguments -> Can be any valid json, but in practice, its often a
	tuple, even empty, for some odd backward compability reasons. 

All events' header must contain an unique message id and the protocol version:

	{
		"message_id": "6ce9503a-bfb8-486a-ac79-e2ed225ace79",
		v: 3
	}

The message id should be unique for the lifetime of the connection between a
client and a server.

> It doest need to be an UUID, but again for some backward compatibility reason
> at dotCloud, we are keeping it UUID style, even if we technically don't
> generate an UUID for every new events anymore, but only a part of it to keep
> it fast.

This document talk only about the version 3 of the protocol.

> The python's implementation has lots of weird pieces of code to handle all
> three versions of the protocol running at dotCloud.

### Multiplexed channels

 - Every new events open a new channel implicitly.
 - The id of the new event will represent the channel id for the connection.
 - Every consecutive events on a channel will have the header field "reply_to"
   set to the channel id:

		{
			"message_id": "6ce9503a-bfb8-486a-ac79-e2ed225ace79",
			"reply_to":	6636fb60-2bca-4ecb-8cb4-bbaaf174e9e6
		}

#### Heartbeat

There is one active heartbeat for every active channel.

> At some point it will be changed to a saner one heartbeat per connection only:
> backward compatibility says hi again.

 - Event's name: '\_zpc\_hb'
 - Event's args: null

Default heartbeat frequency: 5 seconds.

The remote part of a channel is considered lost when no heartbeat event is
received after twice the heartbeat frequency (so 10s by default).

> The python implementation raise the exception LostRemote, and even
> manage to cancel a long-running task on a LostRemote).

#### Buffering (or congestion control) on channels

Both sides have a buffer for incoming messages on a channel.

 - Event's name: '\_zpc\_more'
 - Event's args: integer representing how many entries are available in the client's buffer. 

WIP

## Pattern layer

WIP

Request:
 
 - Event's name: string with the name of the method to call.
 - Event's args: tuple of arguments for the method.

Response:

 - Event's name: string "OK"
 - Event's args: tuple containing the returned value
 
> Note that if the method return a tuple, it is still wrapped inside a tuple
> to contain the returned tuple (backward compatibility man!).

In case of any fatal errors (an exception or the method's name requested can't
be found):

 - Event's name: string "ERR"
 - Event's args: tuple of 3 strings:
 	- Name of the error (Exception's class, or a meanfull word for example).
	- Human representation of the error (prefer english please).
	- If possible a pretty printed traceback of the call stack when the error occured.

### Default methods

WIP

 - \_zerorpc\_ping
 - \_zerorpc\_inspect

### Request/Stream

Response:

 - Event's name: string "STREAM"
 - Event's args: tuple containing the streamed value
 
When the STREAM reach it's end:

 - Event's name: string "STREAM\_DONE"
 - Event's args: null

> The python's implementation represent a stream by an iterator on both sides.

-- END OF DOCUMENT --
