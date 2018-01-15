# set up logging

import os
import logging
# import yaml

from config import cfg

def setuplogging(disc):
    """Setup logging"""

    if not os.path.exists(cfg['LOGPATH']):
        os.makedirs(cfg['LOGPATH'])

    if disc.label == None:
        logfile = "empty.log"
    else:
        logfile = disc.label + ".log"

    if cfg["LOGPATH"][-1:] == "/":
        logfull = cfg["LOGPATH"] + logfile
    else:
        logfull = cfg["LOGPATH"] + "/" + logfile

    # logging = logging.getLogger("ARM")
    # fh = logging.FileHandler(logfull)
    # formatter = logging.formatter('[%(asctime)s] %(name)s: %(levelname)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    # fh.setFormatter(formatter)
    # logging.addHandler(fh)


    logging.basicConfig(filename=logfull, format='[%(asctime)s] ARM: %(levelname)s %(message)s', \
    datefmt='%Y-%m-%d %H:%M:%S', level=logging.DEBUG)

    return  logfull
