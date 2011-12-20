import socket, select
import thread

from clientHandler import ClientHandler
from queues import *

from stats import serverStats

DEFAULT_HOST    = '127.0.0.1'
DEFAULT_PORT    = 22122
DEFAULT_BACKLOG = 10
DEFAULT_TIMEOUT = 60

SERVER_VERSION = '0.1.0'
DEFAULT_PIDFILE = '/var/run/tangery.pid'
DEFAULT_QPATH   = '/var/tangery'

class Server(object):
    
    def __init__(self, opts = {}):
        self.config = {
            'bind':     DEFAULT_HOST,
            'port':     DEFAULT_PORT,
            'backlog':  DEFAULT_BACKLOG,
            'timeout':  DEFAULT_TIMEOUT
        }
        self.config.update(opts)

        if not os.path.exists(DEFAULT_QPATH):
            os.mkdir(DEFAULT_QPATH)

class EventServer(Server):

    queues = NormalQueue(DEFAULT_QPATH)
    poll = select.poll()
    
    clients = {}    

    def new_conn(self):
        conn, addr = self.server.accept()
        conn.setblocking(0)

        self.poll.register(conn.fileno(), select.POLLIN)
        self.clients[conn.fileno()] = ClientHandler(conn, self.queues)

        serverStats['total_connections'] += 1
        serverStats['connections'] += 1

    def handle_client(self, fileno, event):
        client = self.clients[fileno]
        try: 
            if event & select.POLLIN:
                if not client.handleRead(): 
                    raise socket.error

                if client.canWrite():
                    self.poll.register(fileno, select.POLLOUT)
                        
            elif event & select.POLLOUT:
                if not client.handleWrite():
                    raise socket.error

                if client.canRead():
                    self.poll.register(fileno, select.POLLIN)

        except socket.error, e:
            self.poll.unregister(fileno); client.handleClose(); del client
            serverStats['connections'] -= 1
        
    def run(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.server.bind((self.config['bind'], self.config['port']))
        self.server.listen(self.config['backlog'])
        self.server.setblocking(0)

        self.poll.register(self.server.fileno(), select.POLLIN)

        try:
            while True:
                events = self.poll.poll()
                for fileno, event in events:
                    if fileno == self.server.fileno():
                        self.new_conn()
                    else:
                        self.handle_client(fileno, event)
        finally:
            self.poll.unregister(self.server.fileno())
            #self.epoll.close()
            self.server.close()

class ThreadedServer(Server):

    queues = NormalQueue(DEFAULT_QPATH)

    def handle_client(self, conn, addr):
        cl = ClientHandler(conn, self.queues)
        try:
            while True:
                if cl.canRead() and not cl.handleRead():
                    raise socket.error
                if cl.canWrite() and not cl.handleWrite():
                    raise socket.error

        except socket.error, e: pass
        finally: 
            serverStats['connections'] -= 1
            cl.handleClose(); del cl

    def run(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.server.bind((self.config['bind'], self.config['port']))
        self.server.listen(self.config['backlog'])

        try:
            while True:
                conn, addr = self.server.accept()

                serverStats['total_connections'] += 1
                serverStats['connections'] += 1

                thread.start_new_thread(self.handle_client, (conn, addr))
        finally:
            self.server.close()
