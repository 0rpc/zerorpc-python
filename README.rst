zerorpc
=======

zerorpc is a flexible RPC implementation based on zeromq and messagepack. 
Service APIs exposed with zerorpc are called "zeroservices".

zerorpc comes with a convenient script, "zerorpc-client", allowing to:

* expose Python modules without modifying a single line of code,
* call those modules remotely through the command line.


Create a server with a one-liner
--------------------------------

Let's see zerorpc in action with a simple example. In a first terminal,
we will expose the Python "time" module::

  $ zerorpc-client --server --bind tcp://0:1234 time

.. note::
   The bind address uses the zeromq address format. You are not limited
   to TCP transport: you could as well specify ipc:///tmp/time to use
   host-local sockets, for instance. "tcp://0:1234" is a short-hand to
   "tcp://0.0.0.0:1234" and means "listen on TCP port 1234, accepting 
   connections on all IP addresses".


Call the server from the command-line
-------------------------------------

Now, in another terminal, call the exposed module::

  $ zerorpc-client --client --connect tcp://0:1234 strftime %Y/%m/%d
  Connecting to "tcp://0:1234"
  "2011/03/07"

Since the client usecase is the most common one, "--client" is the default
parameter, and you can remove it safely::

  $ zerorpc-client --connect tcp://0:1234 strftime %Y/%m/%d
  Connecting to "tcp://0:1234"
  "2011/03/07"

Moreover, since the most common usecase is to *connect* (as opposed to *bind*)
you can also omit "--connect"::

  $ zerorpc-client tcp://0:1234 strftime %Y/%m/%d
  Connecting to "tcp://0:1234"
  "2011/03/07"


See remote service documentation
--------------------------------

You can introspect the remote service; it happens automatically if you don't
specify the name of the function you want to call::

  $ zerorpc-client tcp://0:1234
  Connecting to "tcp://0:1234"
  tzset       tzset(zone)
  ctime       ctime(seconds) -> string
  clock       clock() -> floating point number
  struct_time <undocumented>
  time        time() -> floating point number
  strptime    strptime(string, format) -> struct_time
  gmtime      gmtime([seconds]) -> (tm_year, tm_mon, tm_mday, tm_hour, tm_min,
  mktime      mktime(tuple) -> floating point number
  sleep       sleep(seconds)
  asctime     asctime([tuple]) -> string
  strftime    strftime(format[, tuple]) -> string
  localtime   localtime([seconds]) -> (tm_year,tm_mon,tm_mday,tm_hour,tm_min,


Specifying non-string arguments
-------------------------------

Now, see what happens if we try to call a function expecting a non-string
argument::

  $ zerorpc-client tcp://0:1234 sleep 3
  Connecting to "tcp://0:1234"
  Traceback (most recent call last):
  [...]
  TypeError: a float is required

That's because all command-line arguments are handled as strings. Don't worry,
we can specify any kind of argument using JSON encoding::

  $ zerorpc-client --json tcp://0:1234 sleep 3
  Connecting to "tcp://0:1234"
  [wait for 3 seconds...]
  null


zeroworkers: reversing bind and connect
---------------------------------------

Sometimes, you don't want your client to connect to the server; you want
your server to act as a kind of worker, and connect to a hub or queue which
will dispatch requests. You can achieve this by swapping "--bind" and
"--connect"::

  $ zerorpc-client --bind tcp://0:1234 localtime

We now have "something" wanting to call the "localtime" function, and waiting
for a worker to connect to it. Let's start the worker::

  $ zerorpc-client --server tcp://0:1234 time

The worker will connect to the listening client and ask him "what should I 
do?"; the client will send the "localtime" function call; the worker will
execute it and return the result. The first program will display the
local time and exit. The worker will remain running.


Listening on multiple addresses
-------------------------------

What if you want to run the same server on multiple addresses? Just repeat
the "--bind" option::

  $ zerorpc-client --server --bind tcp://0:1234 --bind ipc:///tmp/time time

You can then connect to it using either "zerorpc-client tcp://0:1234" or
"zerorpc-client ipc:///tmp/time".

Wait, there is more! You can even mix "--bind" and "--connect". That means
that your server will wait for requests on a given address, *and* connect
as a worker on another. Likewise, you can specify "--connect" multiple times,
so your worker will connect to multiple queues. If a queue is not running,
it won't affect the worker (that's the magic of zeromq).

.. warning:: A client should probably not connect to multiple addresses!

   Almost all other scenarios will work; but if you ask a client to connect
   to multiple addresses, and at least one of them has no server at the end,
   the client will ultimately block. A client can, however, bind multiple
   addresses, and will dispatch requests to available workers. If you want
   to connect to multiple remote servers for high availability purposes,
   you insert something like HAProxy in the middle.
