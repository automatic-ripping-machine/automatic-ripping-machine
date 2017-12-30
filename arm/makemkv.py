#!/usr/bin/python3

import sys
import os
import logging
import subprocess
import time
import logger
import shlex

from config import cfg

def makemkv(logfile, devpath="/dev/sr0", label="something went wrong"):
    # Rip Blurays with MakeMKV
    # logfile = logging.getLogger("logfile")
    logging.info("Starting MakeMKV rip. Method is " + cfg['RIPMETHOD'])

    # get MakeMKV disc number
    logging.debug("Getting MakeMKV disc number")
    cmd='makemkvcon -r info disc:9999  |grep {0} |grep -oP \'(?<=:).*?(?=,)\''.format(
                devpath
    )

    try:
        mdisc = subprocess.check_output(
            cmd,
            shell=True
        ).decode("utf-8")
        logging.info("MakeMKV disc number: " + mdisc.strip())
        # print("mdisc is: " + mdisc)
    except subprocess.CalledProcessError as mdisc_error:
        err = "Call to handbrake failed with code: " + str(mdisc_error.returncode) + "(" + str(mdisc_error.output) + ")"
        logging.error(err)
        # print("Error: " + err)
        return

    #get filesystem in order
    rawpath = os.path.join(cfg['RAWPATH'], label)
    logging.info("rawpath is " + rawpath)

    if not os.path.exists(rawpath):
        try:
            os.makedirs(rawpath)
        except OSError:
            # logging.error("Couldn't create the base file path: " + rawpath + " Probably a permissions error")
            err = "Couldn't create the base file path: " + rawpath + " Probably a permissions error"
    else:
        logging.info(rawpath + " exists.  Adding timestamp.")
        ts = round(time.time() * 100)
        rawpath = os.path.join(cfg['RAWPATH'], label + "_" + str(ts))
        logging.info("rawpath is " + rawpath)
        try:
            os.makedirs(rawpath)
        except OSError:
            # logging.error("Couldn't create the base file path: " + rawpath + " Probably a permissions error")
            err = "Couldn't create the base file path: " + rawpath + " Probably a permissions error"
            sys.exit(err)
        
    # rip bluray
    cmd='makemkvcon backup --decrypt {0} -r disc:{1} {2}>> {3}'.format(
        cfg['MKV_ARGS'],
        mdisc.strip(),
        shlex.quote(rawpath),
        logfile
    )
    logging.info("Backing up with the following command: " + cmd)

    try:
        mkv = subprocess.check_output(
            cmd,
            shell=True
        ).decode("utf-8")
        # print("mkv is: " + mkv)
    except subprocess.CalledProcessError as mdisc_error:
        err = "Call to handbrake failed with code: " + str(mdisc_error.returncode) + "(" + str(mdisc_error.output) + ")"
        logging.error(err)
        # print("Error: " + mkv)
        return

    os.system("eject " + devpath)

    logging.info("Exiting MakeMKV processing with return value of: " + rawpath)
    return(rawpath)

# p=makemkv("/dev/sr0", "bigtest")
# print(p)

# args = entry()

# notify(args.title, args.body)