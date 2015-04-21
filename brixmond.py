#!/usr/bin/env python3

import daemon
import logging
import logging.handlers
import argparse
import os
import configparser
import uuid
import queue
from time import sleep
import requests
import requests.exceptions

from configuration import Configuration
from monitor import MonitorThread
from monitors_base import MonitorCPU, MonitorMem, MonitorDisks, MonitorLoad, MonitorNetwork
from monitors_info import MonitorProcesses, MonitorIP


logger = logging.getLogger('brixmond')
logger.setLevel(logging.DEBUG)

parser = argparse.ArgumentParser(description="BrixIT Monitoring daemon")
parser.add_argument("-d", "--daemon", help="Start in daemon mode", action="store_true")
parser.add_argument("server", help="The address to reach te monitoring server")
parser.add_argument("-f", "--fqdn", help="Override the FQDN reported to the server", default=os.uname()[1])
parser.add_argument("-c", "--configfile", help="Override the config file to use (/etc/brixmond.conf)",
                    default="/etc/brixmond.conf")
args = parser.parse_args()

if args.daemon:
    loghandler = logging.handlers.RotatingFileHandler('/var/log/brixmond.log', maxBytes=1024 * 1024 * 10)
    loghandler.setLevel(logging.DEBUG)
    logger.addHandler(loghandler)
    ctx = daemon.DaemonContext(files_preserve=[loghandler.stream])
    ctx.open()
    logger.info("Entered DaemonContext")
else:
    loghandler = logging.StreamHandler()
    loghandler.setLevel(logging.DEBUG)
    logger.addHandler(loghandler)
    logger.info("Started in foreground")

logger.info("Starting brixmond")
logger.info("Server identifier: {}".format(args.fqdn))

config = configparser.ConfigParser()
config.read(args.configfile)
sections = config.sections()
if not config.has_section("global"):
    config.add_section("global")

secret = config.get("global", "secret", fallback=None)

if secret is None:
    logger.warn("No secret is found. generating new secret")
    secret = str(uuid.uuid4())
    config.set("global", "secret", secret)
    logger.info("New secret: {}".format(secret))
    with open(args.configfile, "w") as configfile:
        config.write(configfile)

logger.info("Connecting to {} to get configuration and update system info".format(args.server))

config = Configuration(args.server, args.fqdn, secret, logger)
config.fetch()

logger.info("Creating result queue")

result_queue = queue.Queue()

logger.info("Starting threads")

monitors = []


def start_monitor(monitor):
    monitor_thread = MonitorThread(monitor=monitor, queue=result_queue)
    monitors.append(monitor_thread)
    monitor_thread.start()

# start all base monitors
start_monitor(MonitorCPU())
start_monitor(MonitorMem())
start_monitor(MonitorDisks())
start_monitor(MonitorLoad())
start_monitor(MonitorNetwork())
start_monitor(MonitorIP())
start_monitor(MonitorProcesses())

# TODO: Add enable/disable monitor in config
if True:
    try:
        from monitors_webserver import MonitorApache
        start_monitor(MonitorApache())
    except Exception:
        logger.error("Cannot load Apache monitor. Python 3.3 required.")

logger.info("Sending data packets every {} seconds".format(config.send_throttle))

while True:
    packet = []
    while not result_queue.empty():
        packet.append(result_queue.get())
    if len(packet) > 0:
        logger.debug("Sending {} packets to the server".format(len(packet)))
        try:
            response = requests.post("http://{}/client/packet/{}/{}".format(args.server, args.fqdn, secret),
                                     json=packet)
            logger.debug("Server response: {}".format(response.status_code))
        except requests.exceptions.ConnectionError as e:
            logger.error("Cannot connect to the server at http://{}".format(args.server))

    sleep(config.send_throttle)