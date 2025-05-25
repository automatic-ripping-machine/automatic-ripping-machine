import platform
import psutil
import re
import subprocess
import logging

from arm.ui import db


class SystemInfo(db.Model):
    """
    Class to hold the system (server) information
    """
    id = db.Column(db.Integer, index=True, primary_key=True)
    name = db.Column(db.String(100))
    cpu = db.Column(db.String(20))
    description = db.Column(db.Unicode(200))
    mem_total = db.Column(db.Float())

    def __init__(self, name="ARM Server", description="Automatic Ripping Machine main server"):
        self.get_cpu_info()
        self.get_memory()
        self.name = name
        self.description = description

    def get_cpu_info(self):
        """
        function to collect and return some cpu info
        ideally want to return {name} @ {speed} Ghz
        """
        self.cpu = "Unable to Identify"
        logging.debug("****** Getting CPU Info ******")

        if platform.system() == "Windows":
            self.cpu = platform.processor()
        elif platform.system() == "Darwin":
            self.cpu = subprocess.check_output(['/usr/sbin/sysctl', "-n", "machdep.cpu.brand_string"]).strip()
        elif platform.system() == "Linux":
            command = "cat /proc/cpuinfo"
            # fulldump = subprocess.check_output(command, shell=True).strip()
            fulldump = subprocess.check_output(command, shell=True).decode()
            # logging.debug(f"Full cpuinfo: {fulldump}")

            # Take any float trailing "MHz", some whitespace, and a colon.
            # like: model name  : Intel(R) Celeron(R) G4930T CPU @ 3.00GHz
            intel_match = re.search(r"model name\s*:\s*(.*?GHz)", fulldump)
            logging.debug(f"Intel output: {intel_match}")
            if intel_match:
                self.cpu = intel_match.group(1)

            # AMD CPU
            amd_name_full = re.search(r"model name\s*:\s*(.*)", fulldump)
            logging.debug(f"AMD output: {amd_name_full}")
            if amd_name_full:
                amd_name = amd_name_full.group(1)
                amd_mhz = re.search(r"cpu MHz\s*:\s*([.0-9]+)", fulldump)  # noqa: W605
                if amd_mhz:
                    amd_ghz = round(float(amd_mhz.group(1)) / 1000, 2)  # this is a good idea
                    self.cpu = str(amd_name) + " @ " + str(amd_ghz) + " GHz"

            # ARM64 CPU
            arm_cpu = re.search(r"model name\s*:\s*(.*)n", fulldump)
            logging.debug(f"ARM64 output: {arm_cpu}")
            if arm_cpu:
                self.cpu = str(arm_cpu.group(1))[:19]

        logging.debug("****************************")

    def get_memory(self):
        """ get the system total memory """
        try:
            memory = psutil.virtual_memory()
            self.mem_total = round(memory.total / 1073741824, 1)
        except EnvironmentError:
            self.mem_total = 0
