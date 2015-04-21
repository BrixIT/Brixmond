import requests
import requests.exceptions
import platform
from cpuinfo import cpuinfo
from time import sleep


class Configuration(object):
    def __init__(self, server, fqdn, secret, logger):
        self.secret = secret
        self.fqdn = fqdn
        self.server = server
        self.logger = logger
        self.send_throttle = 120

        self.monitor_enabled = {
            "apache": False
        }

    def fetch(self):
        configpath = "http://{}/client/config/{}/{}".format(self.server, self.fqdn, self.secret)
        self.logger.debug("Fetching {}".format(configpath))

        sysinfo = {
            "arch": platform.machine(),
            "dist": " ".join(list(platform.linux_distribution())),
            "cpu": cpuinfo.get_cpu_info()["brand"]
        }

        try:
            response = requests.get(configpath, params=sysinfo)
            if response.status_code == 200:
                server_config = response.json()
                if not server_config["enabled"]:
                    self.logger.error("This client hasn't been accepted on the server yet.")
                    self.logger.info("Retrying in {} minutes".format(server_config["polling_time"]))
                    sleep(60 * server_config["polling_time"])
                    self.fetch()
                else:
                    self.logger.info("Config download successful")
                    self.send_throttle = server_config["send_throttle"]
                    self.monitor_enabled = server_config["monitor_enabled"]
            else:
                self.logger.error("Server error {} at http://{}".format(response.status_code, self.server))
                exit(1)
        except requests.exceptions.ConnectionError as e:
            self.logger.error("Cannot connect to the server at http://{}".format(self.server))
            exit(1)