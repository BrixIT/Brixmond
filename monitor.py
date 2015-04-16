import threading
import json
import datetime


class Monitor(object):

    def __init__(self):
        self.name = "monitor"
        self.type = "point"
        self.interval = 1

    def get_point(self):
        return {}


class MonitorThread(threading.Thread):

    def __init__(self, monitor, queue):
        super().__init__()
        self.monitor = monitor
        self.name = monitor.name
        self.type = monitor.type
        self.queue = queue

    def run(self):
        for point in self.monitor.get_point():
            self.queue.put({
                "name": self.name,
                "stamp": datetime.datetime.utcnow().isoformat(),
                "point": json.dumps(point),
                "type": self.type
            })