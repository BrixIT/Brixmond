from monitor import Monitor
import psutil
from time import sleep


class MonitorCPU(Monitor):
    def __init__(self):
        super().__init__()
        self.name = "cpu"
        self.type = "point"

    def get_point(self):
        while True:
            result = []
            for cpu in psutil.cpu_times_percent(interval=60, percpu=True):
                result.append(cpu.__dict__)
            yield result


class MonitorMem(Monitor):
    def __init__(self):
        super().__init__()
        self.name = "mem"
        self.type = "point"

    def get_point(self):
        while True:
            sleep(60)
            yield {"mem": psutil.virtual_memory().__dict__, "swap": psutil.swap_memory().__dict__}


class MonitorLoad(Monitor):
    def __init__(self):
        super().__init__()
        self.name = "load"
        self.type = "point"

    def get_point(self):
        while True:
            sleep(60)
            with open("/proc/loadavg") as loadavg:
                load = loadavg.read().split(" ")[:3]
            yield load


class MonitorNetwork(Monitor):
    def __init__(self):
        super().__init__()
        self.name = "net"
        self.type = "point"

    def get_point(self):
        counters_old = psutil.net_io_counters().__dict__
        while True:
            sleep(60)
            conn_counters = {
                "ESTABLISHED": 0,
                "SYN_SENT": 0,
                "SYN_RECV": 0,
                "CLOSING": 0,
                "LISTEN": 0,
                "TIME_WAIT": 0,
                "LAST_ACK": 0,
                "FIN_WAIT2": 0,
                "FIN_WAIT1": 0,
                "CLOSE_WAIT": 0,
                "NONE": 0,
            }

            for connection in psutil.net_connections():
                conn_counters[connection.status] += 1

            conn_semantic = {
                "connected": conn_counters["ESTABLISHED"],
                "connecting": conn_counters["SYN_SENT"] + conn_counters["SYN_RECV"],
                "closing": conn_counters["CLOSING"] + conn_counters["LAST_ACK"] + conn_counters["FIN_WAIT1"] +
                           conn_counters["FIN_WAIT2"] + conn_counters["CLOSE_WAIT"] + conn_counters["TIME_WAIT"],
                "listening": conn_counters["LISTEN"],
                "unknown": conn_counters["NONE"]
            }

            counters = psutil.net_io_counters().__dict__
            counters_delta = {key: counters[key] - counters_old.get(key, 0) for key in counters.keys()}
            counters_old = counters
            result = {
                "counters": counters_delta,
                "sockets": conn_semantic
            }
            yield result



