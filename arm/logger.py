# set up logging

import os
import logging
# import yaml

from config import cfg

def setuplogging():
    """Setup logging"""

    # with open("/opt/parm/docs/config.yaml", "r") as f:
    #     cfg = yaml.load(f)

    # print(cfg['LOGPATH'])

    if not os.path.exists(cfg['LOGPATH']):
        os.makedirs(cfg['LOGPATH'])

    if str(os.getenv('ID_FS_LABEL')) == "None":
        logfile = "empty.log"
    else:
        logfile = str(os.getenv('ID_FS_LABEL')) + ".log"

    if cfg["LOGPATH"][-1:] == "/":
        logfull = cfg["LOGPATH"] + logfile
    else:
        logfull = cfg["LOGPATH"] + "/" + logfile

    logging.basicConfig(filename=logfull, format='[%(asctime)s] ARM: %(levelname)s %(message)s', \
    datefmt='%Y-%m-%d %H:%M:%S', level=logging.DEBUG)

    return  logfull
