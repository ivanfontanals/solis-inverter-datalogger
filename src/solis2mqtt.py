#!/usr/bin/python3

import minimalmodbus
import yaml
import daemon
import logging
from logging.handlers import RotatingFileHandler
import argparse
from time import sleep
from datetime import datetime
from threading import Lock
from inverter import Inverter
from config import Config
from minimalmodbus import BYTEORDER_LITTLE

VERSION = "0.7"

class Solis2Mqtt:
    def __init__(self):    
        self.cfg = Config('config.yaml')
        self.register_cfg = ...
        self.load_register_cfg()
        self.inverter = Inverter(self.cfg['device'], self.cfg['slave_address'])
        self.inverter_lock = Lock()
        self.inverter_offline = False

    def load_register_cfg(self, register_data_file='solis_modbus.yaml'):
        with open(register_data_file) as smfile:
            self.register_cfg = yaml.load(smfile, yaml.Loader)

    
    def read_composed_date(self, register, functioncode):
        year = self.inverter.read_register(register[0], functioncode=functioncode)
        month = self.inverter.read_register(register[1], functioncode=functioncode)
        day = self.inverter.read_register(register[2], functioncode=functioncode)
        hour = self.inverter.read_register(register[3], functioncode=functioncode)
        minute = self.inverter.read_register(register[4], functioncode=functioncode)
        second = self.inverter.read_register(register[5], functioncode=functioncode)
        return f"20{year:02d}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:{second:02d}"

    

    def main(self):
        # Write headers
        for entry in self.register_cfg:
            if not entry['active']: 
                continue
            print(f"{entry['name']}|",end = " ")
        print("")

        while True:
            #logging.info("Inverter scan start at " + datetime.now().isoformat())
            registers_map = {}
            for entry in self.register_cfg:
                if not entry['active'] or 'function_code' not in entry['modbus'] :
                    continue

                try:
                    if entry['modbus']['read_type'] == "register":
                        with self.inverter_lock:
                            value = self.inverter.read_register(entry['modbus']['register'],
                                                                number_of_decimals=entry['modbus']['number_of_decimals'],
                                                                functioncode=entry['modbus']['function_code'],
                                                                signed=entry['modbus']['signed'])

                    elif entry['modbus']['read_type'] == "long":
                        with self.inverter_lock:
                            value = self.inverter.read_long(entry['modbus']['register'],
                                                            functioncode=entry['modbus']['function_code'],
                                                            signed=entry['modbus']['signed'])
                    elif entry['modbus']['read_type'] == "composed_datetime":
                        with self.inverter_lock:
                            value = self.read_composed_date(entry['modbus']['register'],
                                                            functioncode=entry['modbus']['function_code'])
                # NoResponseError occurs if inverter is off,
                # InvalidResponseError might happen when inverter is starting up or shutting down during a request
                except (minimalmodbus.NoResponseError, minimalmodbus.InvalidResponseError):
                    logging.error("ERROR!!")
                    if not self.inverter_offline:
                        logging.info("Inverter not reachable")
                        self.inverter_offline = True

                    
                else:
                    self.inverter_offline = False

                #self.mqtt.publish(f"{self.cfg['inverter']['name']}/{entry['name']}", value, retain=True)
                registers_map[entry['name']] = value
                #logging.info(f"{self.cfg['inverter']['name']}/{entry['name']}, value: {value}")
            for key in registers_map.keys():
                print(f"{registers_map[key]}|",end = " ")
            print("")

            # wait with next poll configured interval, or if inverter is not responding ten times the interval
            sleep_duration = self.cfg['poll_interval'] if not self.inverter_offline else self.cfg['poll_interval_if_off']
            logging.debug(f"Inverter scanning paused for {sleep_duration} seconds")
            sleep(sleep_duration)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Solis inverter to mqtt bridge.')
    parser.add_argument('-d', '--daemon', action='store_true', help='start as daemon')
    parser.add_argument('-v', '--verbose', action='store_true', help="verbose logging")
    args = parser.parse_args()

    def start_up(is_daemon, verbose):
        log_level = logging.DEBUG if verbose else logging.INFO
        handler = RotatingFileHandler("solis2mqtt.log", maxBytes=1024 * 1024 * 10,
                                      backupCount=1) if is_daemon else logging.StreamHandler()
        logging.basicConfig(level=log_level, format="%(asctime)s - %(name)s - %(message)s", handlers=[handler])
        logging.info("Starting up...")
        Solis2Mqtt().main()

    if args.daemon:
        with daemon.DaemonContext(working_directory='./'):
            try:
                start_up(args.daemon, args.verbose)
            except:
                logging.exception("Unhandled exception:")
    else:
        start_up(args.daemon, args.verbose)