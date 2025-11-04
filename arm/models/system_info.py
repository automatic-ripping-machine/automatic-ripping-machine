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
            fulldump = subprocess.check_output(command, shell=True).decode()

            # Find the CPU Model Name
            # Intel     model name  : Intel(R) Celeron(R) G4930T CPU @ 3.00GHz
            # amd       model name  : AMD Ryzen 5 3600 6-Core Processor
            # arm       model name  : ARMv8 Processor rev 3 (v8l)
            # arm alt  Model : Raspberry Pi 4 Model B Rev 1.2
            regex_match = re.search(r"(?:model name|Model)\s*:\s*(.*)", fulldump, re.IGNORECASE)

            logging.debug(f"Regex output: {regex_match}")
            if regex_match:
                self.cpu = regex_match.group(1)

        logging.debug(f"CPU Info: {self.cpu}")
        logging.debug("****************************")

    def get_memory(self):
        """ get the system total memory """
        try:
            memory = psutil.virtual_memory()
            self.mem_total = round(memory.total / 1073741824, 1)
        except EnvironmentError:
            self.mem_total = 0
