"""
Source:
http://chimera.labs.oreilly.com/books/1230000000393/ch12.html#_solution_209

Tweaked by me to make it work
"""

import queue
import socket
import os

class PollableQueue(queue.Queue):

    def __init__(self):

        queue.Queue.__init__(self)

        # Create a pair of connected sockets
        if os.name == 'posix':
            self._putsocket, self._getsocket = socket.socketpair()
        else:
            # Compatibility on non-POSIX systems
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.bind(('127.0.0.1', 0))
            server.listen(1)
            self._putsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._putsocket.connect(server.getsockname())
            self._getsocket, _ = server.accept()
            server.close()

    def fileno(self):
        return self._getsocket.fileno()

    def put(self, item):
        queue.Queue.put(self, item)
        self._putsocket.send(b'x')

    def get(self):
        self._getsocket.recv(1)
        return queue.Queue.get(self)
