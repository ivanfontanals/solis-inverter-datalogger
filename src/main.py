#!/usr/bin/python3

import minimalmodbus
import argparse
import daemon
import logging
from logging.handlers import RotatingFileHandler
from solis2mqtt import Solis2Mqtt

def start_up(is_daemon, verbose):
        log_level = logging.DEBUG if verbose else logging.INFO
        handler = RotatingFileHandler("solis2mqtt.log", maxBytes=1024 * 1024 * 10,
                                      backupCount=1) if is_daemon else logging.StreamHandler()
        logging.basicConfig(level=log_level, format="%(asctime)s - %(name)s - %(message)s", handlers=[handler])
        logging.info("Starting up...")
        Solis2Mqtt().main()


def main():
    parser = argparse.ArgumentParser(description='Solis inverter to mqtt bridge.')
    parser.add_argument('-d', '--daemon', action='store_true', help='start as daemon')
    parser.add_argument('-v', '--verbose', action='store_true', help="verbose logging")
    args = parser.parse_args()

    if args.daemon:
        with daemon.DaemonContext(working_directory='./'):
            try:
                start_up(args.daemon, args.verbose)
            except:
                logging.exception("Unhandled exception:")
    else:
        start_up(args.daemon, args.verbose)

if __name__ == '__main__':
    main()