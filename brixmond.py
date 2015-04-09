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
from base_monitors import MonitorCPU, MonitorMem, MonitorDisks, MonitorLoad, MonitorNetwork

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

cpu = MonitorThread(monitor=MonitorCPU(), queue=result_queue)
cpu.start()

mem = MonitorThread(monitor=MonitorMem(), queue=result_queue)
mem.start()

disks = MonitorThread(monitor=MonitorDisks(), queue=result_queue)
disks.start()

load = MonitorThread(monitor=MonitorLoad(), queue=result_queue)
load.start()

net = MonitorThread(monitor=MonitorNetwork(), queue=result_queue)
net.start()

logger.info("Sending data packets every {} seconds".format(config.send_throttle))

while True:
    packet = []
    while not result_queue.empty():
        packet.append(result_queue.get())
    if len(packet) > 0:
        logger.debug("Sending {} packets to the server".format(len(packet)))
        try:
            response = requests.post("http://{}/client/packet/{}/{}".format(args.server, args.fqdn, secret),
                                     data=packet, json=True)
            logger.debug("Server response: {}".format(response.status_code))
        except requests.exceptions.ConnectionError as e:
            logger.error("Cannot connect to the server at http://{}".format(args.server))

    sleep(config.send_throttle)