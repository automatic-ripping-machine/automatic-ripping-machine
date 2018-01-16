# set up logging

import os
import logging
# import yaml

from config import cfg

def setuplogging(disc):
    """Setup logging and return the path to the logfile for 
    redirection of external calls"""

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

    if cfg["LOGLEVEL"] == "DEBUG":
        logging.basicConfig(filename=logfull, format='[%(asctime)s] %(levelname)s ARM: %(module)s.%(funcName)s %(message)s', \
        datefmt='%Y-%m-%d %H:%M:%S', level=cfg["LOGLEVEL"])
    else:
        logging.basicConfig(filename=logfull, format='[%(asctime)s] %(levelname)s ARM: %(message)s', \
        datefmt='%Y-%m-%d %H:%M:%S', level=cfg["LOGLEVEL"])

    return  logfull
