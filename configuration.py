import requests
import platform
from cpuinfo import cpuinfo


class Configuration(object):
    def __init__(self, server, fqdn, secret, logger):
        self.secret = secret
        self.fqdn = fqdn
        self.server = server
        self.logger = logger
        self.send_throttle = 120

    def fetch(self):
        configpath = "http://{}/client/config/{}/{}".format(self.server, self.fqdn, self.secret)
        self.logger.debug("Fetching {}".format(configpath))

        sysinfo = {
            "arch": platform.machine(),
            "dist": " ".join(list(platform.linux_distribution())),
            "cpu": cpuinfo.get_cpu_info()["brand"]
        }

        response = requests.get(configpath, params=sysinfo)
        # TODO:set send_throttle from response