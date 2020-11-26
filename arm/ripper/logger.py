# set up logging

import os
import logging
import time

from arm.config.config import cfg


def setuplogging(job):
    """Setup logging and return the path to the logfile for
    redirection of external calls"""

    ##Make the log dir if it doesnt exist
    if not os.path.exists(cfg['LOGPATH']):
        os.makedirs(cfg['LOGPATH'])

    if job.label == "" or job.label is None:
        if job.disctype == "music":
            logfile = "music_cd.log"
        else:
            logfile = "empty.log"
    else:
        logfile = job.label + ".log"

    ## TODO: fix the database is getting the wrong log file
    ## Added from pull 366 But added if statement so we dont touch the empty.log
    if logfile != "empty.log":
        ## Does the logpath have a / add it if we dont
        if cfg['LOGPATH'][-1:] == "/":
            #Check to see if file already exists, if so, create a new file
            TmpLogFull = cfg['LOGPATH'] + logfile
            logfull = cfg['LOGPATH'] + str(job.label) + "_" + str(round(time.time() * 100)) + ".log" if os.path.isfile(TmpLogFull) else  cfg['LOGPATH'] + logfile
        else:
            #Check to see if file already exists, if so, create a new file
            TmpLogFull = cfg['LOGPATH'] + "/" + logfile
            logfull = cfg['LOGPATH'] + "/" + str(job.label) + "_" + str(round(time.time() * 100)) + ".log" if os.path.isfile(TmpLogFull) else  cfg['LOGPATH'] + "/" + logfile
    else:
        ## For empty.log we need to set logfull
        logfull = cfg['LOGPATH'] + logfile if cfg['LOGPATH'][-1:] == "/" else cfg['LOGPATH'] + "/" + logfile

    ## Debug formatting
    if cfg['LOGLEVEL'] == "DEBUG":
        ## TODO: make secret keys safe
        logging.basicConfig(filename=logfull, format='[%(asctime)s] %(levelname)s ARM: %(module)s.%(funcName)s %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S', level=cfg['LOGLEVEL'])
    else:
        logging.basicConfig(filename=logfull, format='[%(asctime)s] %(levelname)s ARM: %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S', level=cfg['LOGLEVEL'])

    ## we need to give the right logfile to database
    job.logfile = logfull

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
