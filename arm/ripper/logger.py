# set up logging

import os
import logging
import time

# from arm.config.config import cfg


def setuplogging(job):
    """Setup logging and return the path to the logfile for
    redirection of external calls"""

    if not os.path.exists(job.config.LOGPATH):
        os.makedirs(job.config.LOGPATH)

    if job.label == "" or job.label is None:
        if job.disctype == "music":
            logfile = "music_cd.log"
        else:
            logfile = "empty.log"
    else:
        logfile = job.label + ".log"

    if job.config.LOGPATH[-1:] == "/":
        logfull = job.config.LOGPATH + logfile
    else:
        logfull = job.config.LOGPATH + "/" + logfile

    if job.config.LOGLEVEL == "DEBUG":
        logging.basicConfig(filename=logfull, format='[%(asctime)s] %(levelname)s ARM: %(module)s.%(funcName)s %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S', level=job.config.LOGLEVEL)
    else:
        logging.basicConfig(filename=logfull, format='[%(asctime)s] %(levelname)s ARM: %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S', level=job.config.LOGLEVEL)

    job.logfile = logfile

    return logfull


def cleanuplogs(logpath, loglife):
    """Delete all log files older than x days\n
    logpath = path of log files\n
    loglife = days to let logs live\n

    """

    now = time.time()
    logging.info("Looking for log files older than " + str(loglife) + " days old.")

    for filename in os.listdir(logpath):
        fullname = os.path.join(logpath, filename)
        if fullname.endswith(".log"):
            if os.stat(fullname).st_mtime < now - loglife * 86400:
                logging.info("Deleting log file: " + filename)
                os.remove(fullname)
