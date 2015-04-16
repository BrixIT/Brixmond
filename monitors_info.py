from monitor import Monitor
import psutil
from time import sleep
import netifaces


class MonitorProcesses(Monitor):
    def __init__(self):
        super().__init__()
        self.name = "processes"
        self.type = "info"
        for process in psutil.process_iter():
            process.cpu_percent()

    def get_point(self):
        while True:
            sleep(120)
            processes = []
            for process in psutil.process_iter():
                processes.append({
                    "name": " ".join(process.cmdline()),
                    "cpu": process.cpu_percent(),
                    "mem": process.memory_percent()
                })

            sorted_processes = sorted(processes, key=lambda k: k['cpu'], reverse=True)
            yield sorted_processes[0:5]


class MonitorIP(Monitor):
    def __init__(self):
        super().__init__()
        self.name = "ip"
        self.type = "info"

    def get_point(self):
        while True:
            result = {}
            for interface in netifaces.interfaces():
                if interface != "lo":
                    addresses = netifaces.ifaddresses(interface)
                    block = {"v4": addresses[netifaces.AF_INET]}
                    if netifaces.AF_INET6 in addresses:
                        block["v6"] = addresses[netifaces.AF_INET6]
                    result[interface] = block
            yield result
            sleep(60)