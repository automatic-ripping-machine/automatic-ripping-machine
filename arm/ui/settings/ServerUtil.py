"""
Class definition
 Server - class for managing system utilisation
"""

import psutil

import arm.config.config as cfg
from arm.ui import app
from flask import flash


class ServerUtil():
    cpu_util = 0.0
    cpu_temp = 0.0
    memory_free = 0.0
    memory_used = 0.0
    memory_percent = 0.0
    # Hard drive space
    storage_transcode_free = 0
    storage_transcode_percent = 0.0
    storage_completed_free = 0
    storage_completed_percent = 0.0

    def __init__(self):
        self.get_update()

    def get_update(self):
        self.get_cpu_util()
        self.get_cpu_temp()
        self.get_memory()
        self.storage_transcode_free, self.storage_transcode_percent = \
            self.get_disk_space(cfg.arm_config['TRANSCODE_PATH'])
        self.storage_completed_free, self.storage_completed_percent = \
            self.get_disk_space(cfg.arm_config['COMPLETED_PATH'])

    def get_cpu_util(self):
        try:
            self.cpu_util = psutil.cpu_percent()
        except EnvironmentError:
            self.cpu_util = 0
        app.logger.debug(f"Server CPU Util: {self.cpu_util}")

    def get_cpu_temp(self):
        try:
            temps = psutil.sensors_temperatures()
            app.logger.debug(f"cpu_temp: {temps}")

            # cpu temperature - intel systems
            if coretemp := temps.get('coretemp', None):
                self.cpu_temp = coretemp[0][1]

            # cpu temperature - AMD systems
            elif atk0110 := temps.get('cpu_thermal', None):
                self.cpu_temp = atk0110[0][1]

            # cpu temperature - AMD systems (Phenom)
            elif nct6797 := temps.get('cpu_thermal', None):
                self.cpu_temp = nct6797[0][1]

            # cpu temperature - PI
            elif cpu_thermal := temps.get('cpu_thermal', None):
                self.cpu_temp = cpu_thermal[0][1]

            # cpu temperature - AMD systems (generic)
            elif k10temp := temps.get('k10temp', None):
                self.cpu_temp = k10temp[0][1]

            # cpu temperature - unknown devices
            else:
                self.cpu_temp = 0
        except EnvironmentError:
            self.cpu_temp = 0
        app.logger.debug(f"Server CPU Temp:  {self.cpu_temp}")

    def get_memory(self):
        try:
            memory = psutil.virtual_memory()
            self.memory_free = round(memory.available / 1073741824, 1)
            self.memory_used = round(memory.used / 1073741824, 1)
            self.memory_percent = memory.percent
        except EnvironmentError:
            self.memory_free = 0
            self.memory_used = 0
            self.memory_percent = 0
        app.logger.debug(f"Server Mem Free:  {self.memory_free}")
        app.logger.debug(f"Server Mem Used:  {self.memory_used}")
        app.logger.debug(f"Server Mem Percent:  {self.memory_percent}")

    def get_disk_space(self, filepath):
        # Hard drive space
        try:
            disk_space = psutil.disk_usage(filepath).free
            disk_space = round(disk_space / 1073741824, 1)
            disk_percent = psutil.disk_usage(filepath).percent
        except FileNotFoundError:
            disk_space = 0
            disk_percent = 0
            app.logger.debug("ARM folders not found")
            flash("There was a problem accessing the ARM folder: "
                  f"'{filepath}'. Please make sure you have setup ARM", "danger")
        app.logger.debug(f"Server {filepath} Space:  {disk_space}")
        app.logger.debug(f"Server {filepath} Percent:  {disk_percent}")
        return disk_space, disk_percent
