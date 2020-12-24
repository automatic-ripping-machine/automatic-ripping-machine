# set up logging

import os
import logging
import time

from arm.config.config import cfg
from arm.ripper import getmusictitle


def setuplogging(job):
    """Setup logging and return the path to the logfile for
    redirection of external calls"""

    # Make the log dir if it doesnt exist
    if not os.path.exists(cfg['LOGPATH']):
        os.makedirs(cfg['LOGPATH'])

    # This isnt catching all of them
    if job.label == "" or job.label is None:
        if job.disctype == "music":
            # Use the muscis label if we can find it - defaults toi music_cd.log
            discid = getmusictitle.get_discid(job)
            title = getmusictitle.gettitle(discid, job)
            if title != "not identified":
                logfile1 = str(title) + ".log"
                logfile = logfile1.replace(" ", "_")
            else:
                job.title = "not identified"
                job.label = "not identified"
                job.logfile = "music_cd.log"
                logfile = "music_cd.log"
        else:
            logfile = "empty.log"
        # set a logfull for empty.log and music_cd.log
        logfull = cfg['LOGPATH'] + logfile if cfg['LOGPATH'][-1:] == "/" else cfg['LOGPATH'] + "/" + logfile
    else:
        logfile = job.label + ".log"
        if cfg['LOGPATH'][-1:] == "/":
            # This really needs to be cleaned up, but it works for now
            # Check to see if file already exists, if so, create a new file
            newlogfile = str(job.label) + "_" + str(round(time.time() * 100)) + ".log"
            TmpLogFull = cfg['LOGPATH'] + logfile
            logfile = newlogfile if os.path.isfile(TmpLogFull) else logfile
            logfull = cfg['LOGPATH'] + newlogfile if os.path.isfile(TmpLogFull) else cfg['LOGPATH'] + str(job.label) + ".log "
        else:
            # Check to see if file already exists, if so, create a new file
            newlogfile = str(job.label) + "_" + str(round(time.time() * 100)) + ".log"
            TmpLogFull = cfg['LOGPATH'] + "/" + logfile
            logfile = newlogfile if os.path.isfile(TmpLogFull) else str(job.label)
            logfull = cfg['LOGPATH'] + "/" + newlogfile if os.path.isfile(TmpLogFull) else cfg['LOGPATH'] + "/" + str(job.label) + ".log"

        # We need to give the logfile only to database
        job.logfile = logfile

    # Debug formatting
    if cfg['LOGLEVEL'] == "DEBUG":
        logging.basicConfig(filename=logfull, format='[%(asctime)s] %(levelname)s ARM: %(module)s.%(funcName)s %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S', level=cfg['LOGLEVEL'])
    else:
        logging.basicConfig(filename=logfull, format='[%(asctime)s] %(levelname)s ARM: %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S', level=cfg['LOGLEVEL'])
    # This stops apprise spitting our secret keys when users posts online
    apprise_logger = logging.getLogger('apprise')
    apprise_logger.setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    # logging.debug("Logfull = " + logfull)
    # Return the full logfile location to the logs
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
