from persistent_queue import PersistentQueue
from stats import serverStats
import os.path

class NormalQueue(object):
    def __init__(self, persistent_path):
        self.qspath = persistent_path
        self.queues = {}

    def countItems(self):
        return sum(
            map(len, self.queues.values())
        )

    def getQueue(self, key, create = False):
        queue = self.queues.get(key)
        if queue is None and create:
            queue = PersistentQueue(os.path.join(self.qspath, key))
            serverStats['current_bytes'] += queue.initialBytes
            serverStats['total_items'] += queue.total_items

            self.queues[key] = queue

        return queue

    def put(self, key, data):
        serverStats['set_requests'] += 1

        queue = self.getQueue(key, create = True)
        queue.append(data)

        serverStats['current_bytes'] += len(data)
        serverStats['total_items'] += 1

    def get(self, key):
        serverStats['get_requests'] += 1
        
        queue = self.getQueue(key, create = True)
        if len(queue) == 0:
            serverStats['get_misses'] += 1
            return (0, 0, None)

        data = queue.popleft()

        serverStats['get_hits'] += 1
        serverStats['current_bytes'] -= len(data)
        
        return data

    def delete(self, key):
        queue = self.queues.get(key, None)
        if queue:
            queue.clear()

