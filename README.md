# tangery

Tangery is a python implementation of a simple, distributed message queue, (async queues) heavily based on Blaine Cook's 'starling' and Robey Pointer's 'kestrel' projects.

It implements the memcached protocol to communicate with clients, so you can use whatever memcached client lib you like to store and retrieve objects from the queues. 

It stores queues in disk, so in case something happens on the server you don't loose the messages stored in queues.

It is also built with performance in mind. 
