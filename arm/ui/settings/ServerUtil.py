"""
Class definition
 Server - class for managing system utilisation
"""
import platform
import psutil
import re
import subprocess
import psutil
from flask import current_app as app

import config.config as cfg
from flask import flash


class ServerUtil():
    cpu: str = ""
    cpu_util: float = 0.0
    cpu_temp: float = 0.0
    mem_total: float = 0.0
    memory_free: float = 0.0
    memory_used: float = 0.0
    memory_percent: float = 0.0
    # Hard drive space
    storage_transcode_free: int = 0
    storage_transcode_percent: float = 0.0
    storage_completed_free: int = 0
    storage_completed_percent: float = 0.0

    def __init__(self):
        self.get_cpu_info()
        self.get_update()

    def get_update(self):
        self.get_cpu_util()
        self.get_cpu_temp()
        self.get_memory()
        self.storage_transcode_free, self.storage_transcode_percent = \
            self.get_disk_space(cfg.arm_config['TRANSCODE_PATH'])
        self.storage_completed_free, self.storage_completed_percent = \
            self.get_disk_space(cfg.arm_config['COMPLETED_PATH'])

    def get_cpu_info(self):
        """
        function to collect and return some cpu info
        ideally want to return {name} @ {speed} Ghz
        """
        self.cpu = "Unknown"
        if platform.system() == "Windows":
            self.cpu = platform.processor()
        elif platform.system() == "Darwin":
            self.cpu = subprocess.check_output(['/usr/sbin/sysctl', "-n", "machdep.cpu.brand_string"]).strip()
        elif platform.system() == "Linux":
            command = "cat /proc/cpuinfo"
            fulldump = str(subprocess.check_output(command, shell=True).strip())
            # Take any float trailing "MHz", some whitespace, and a colon.
            speeds = re.search(r"\\nmodel name\\t:.*?GHz\\n", fulldump)
            if speeds:
                # We have intel CPU
                speeds = str(speeds.group())
                speeds = speeds.replace('\\n', ' ')
                speeds = speeds.replace('\\t', ' ')
                speeds = speeds.replace('model name :', '')
                self.cpu = speeds
            # AMD CPU
            amd_name_full = re.search(r"model name\\t: (.*?)\\n", fulldump)
            if amd_name_full:
                amd_name = amd_name_full.group(1)
                amd_mhz = re.search(r"cpu MHz(?:\\t)*: ([.0-9]*)\\n", fulldump)  # noqa: W605
                if amd_mhz:
                    amd_ghz = round(float(amd_mhz.group(1)) / 1000, 2)  # this is a good idea
                    self.cpu = str(amd_name) + " @ " + str(amd_ghz) + " GHz"
            # ARM64 CPU
            arm_cpu = re.search(r"\\nmodel name\\t:(.*?)\\n", fulldump)
            if arm_cpu:
                self.cpu = str(arm_cpu.group(1))[:19]

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
            self.mem_total = round(memory.total / 1073741824, 1)
            self.memory_free = round(memory.available / 1073741824, 1)
            self.memory_used = round(memory.used / 1073741824, 1)
            self.memory_percent = memory.percent
        except EnvironmentError:
            self.mem_total = 0
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
