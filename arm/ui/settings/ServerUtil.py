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

    def get_cpu_temp(self):
        try:
            temps = psutil.sensors_temperatures()
            if coretemp := temps.get('coretemp', None):
                self.cpu_temp = coretemp[0][1]
            else:
                self.cpu_temp = 0
        except EnvironmentError:
            self.cpu_temp = 0

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
        return disk_space, disk_percent
