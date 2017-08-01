"""
Utility functions to send and receive data through ZMQ sockets.

From the ZMQ Guide:

ZeroMQ doesn't know anything about the data you send except its size in bytes. That means you are responsible for formatting it safely so that applications can read it back. Doing this for objects and complex data types is a job for specialized libraries like Protocol Buffers. But even for strings, you need to take care.
"""

import pickle

def send (socket, data):
    data_bytes = pickle.dumps (data, -1)
    socket.send (data_bytes)

def recv (socket):
    data_bytes = socket.recv ()
    data = pickle.loads (data_bytes)
    return data

def send_recv (socket, data):
    send (socket, data)
    return recv (socket)
