#!/usr/bin/python3

import sys
import argparse
import os
import subprocess
import logging
import time
import shutil
import requests
import shlex
import logger
import pyudev
import datetime
import utils
import makemkv
import handbrake
import classes
import identify

from config import cfg

def entry():
    """ Entry to program, parses arguments"""
    parser = argparse.ArgumentParser(description='Process disc using ARM')
    # parser.add_argument('-l', '--label', help='Label', required=True)
    parser.add_argument('-d', '--devpath', help='Devpath', required=True)
    # parser.add_argument('-t', '--videotitle', help='Video Title', required=True)
    # parser.add_argument('-y', '--videotype', help='Video Type', required=True)
    # parser.add_argument('-e', '--label', help='Label', required=True)
    # parser.add_argument('-n', '--hasnicetitle', help="Has Nice Title", required=False)
    # parser.add_argument('-b', '--isbluray', help="Is Bluray", default="false", required=False)

    return parser.parse_args()

def log_udev_params():
    """log all udev paramaters"""

    logging.debug("**** Logging udev attributes ****")
    # logging.info("**** Start udev attributes ****")
    context = pyudev.Context()
    device = pyudev.Devices.from_device_file(context, '/dev/sr0')
    for key, value in device.items():
        logging.debug(key + ":" + value)
    logging.debug("**** End udev attributes ****")

def log_arm_params(disc):
    """log all entry parameters"""

    #log arm parameters
    # logging.info("Logging dvd parameters")
    logging.info("**** Logging ARM paramaters ****")
    logging.info("devpath: " + str(disc.devpath))
    logging.info("mountpoint: " + str(disc.mountpoint))
    logging.info("videotitle: " + str(disc.videotitle))
    logging.info("videoyear: " + str(disc.videoyear))
    logging.info("videotype: " + str(disc.videotype))
    logging.info("hasnicetitle: " + str(disc.hasnicetitle))
    logging.info("disctype: " + str(disc.disctype))
    logging.info("mainfeature: " + cfg['MAINFEATURE'])
    logging.info("minlength: " + cfg['MINLENGTH'])
    logging.info("maxlength: " + cfg['MAXLENGTH'])
    logging.info("hb_preset: " + cfg['HB_PRESET'])
    logging.info("hb_args: " + cfg['HB_ARGS'])
    logging.info("logfile: " + logfile)
    logging.info("media_dir: " + cfg['MEDIA_DIR'])
    logging.info("extras_sub: " + cfg['EXTRAS_SUB'])
    logging.info("emby_refresh: " + cfg['EMBY_REFRESH'])
    logging.info("emby_subfolders: " + cfg['EMBY_SUBFOLDERS'])
    logging.info("emby_server: " + cfg['EMBY_SERVER'])
    logging.info("emby_port: " + cfg['EMBY_PORT'])
    logging.info("**** End of ARM parameters ****")

def main(logfile, disc):
    """main dvd processing function"""
    logging.info("Starting Disc identification")

    identify.identify(disc)

    log_arm_params(disc)

    # sys.exit()

    utils.notify("ARM notification", "Found disc: " + str(disc.videotitle) + ". Video type is " + str(disc.videotype) + ". Main Feature is " + cfg['MAINFEATURE'] + ".")

    #get filesystem in order
    hboutpath = os.path.join(cfg['ARMPATH'], str(disc.videotitle))

    if not os.path.exists(hboutpath):
        logging.debug("Creating directory: " + hboutpath)
        try:
            os.makedirs(hboutpath)
        except OSError:
            logging.error("Couldn't create the base file path: " + hboutpath + " Probably a permissions error")
            err = "Couldn't create the base file path: " + hboutpath + " Probably a permissions error"
            sys.exit(err)
    else:
        ts = round(time.time() * 100)
        hboutpath = os.path.join(cfg['ARMPATH'], str(disc.videotitle) + "_" + str(ts))
        try:
            os.makedirs(hboutpath)
        except OSError:
            err = "Couldn't create the base file path: " + hboutpath + " Probably a permissions error"
            logging.error(err)
            sys.exit(err)
    
    hbinpath = str(disc.devpath)
    if disc.disctype == "bluray":
        #send to makemkv for ripping
        if cfg['RIPMETHOD'] == "backup":
            #backup method
            #run MakeMKV and get path to ouput
            mkvoutpath = makemkv.makemkv(logfile, str(disc.devpath), str(disc.videotitle))
            if mkvoutpath is None:
                logging.error("MakeMKV did not complete successfully.  Exiting ARM!")
                sys.exit()
            #point HB to the path MakeMKV ripped to
            hbinpath = mkvoutpath
        # else:
            #currently do nothing

    if disc.videotype == "movie" and cfg['MAINFEATURE'] == "true":
        handbrake.handbrake_mainfeature(hbinpath, hboutpath, str(disc.videotitle), logfile, disc.hasnicetitle)
    else:
        # handbrake_all(hboutpath, logfile)
        handbrake.handbrake_all(hbinpath, hboutpath, str(disc.videotitle), logfile, disc.hasnicetitle, str(disc.videotype))

    if disc.disctype == "bluray":
        shutil.rmtree(mkvoutpath)

    utils.notify("ARM notification", str(disc.videotitle) + " processing complete.")

    logging.info("Transcoding comlete")

if __name__ == "__main__":
    args = entry()
    # sys.exit()
    # print(args.devpath)
    devpath = "/dev/" + args.devpath
    print(devpath)

    disc = classes.Disc(devpath)
    print (disc.label)

    logfile = logger.setuplogging(disc)
    # log = logging.getLogger(__name__)

    if disc.label == None:
        logging.info("Drive appears to be empty.  Exiting ARM.")
        sys.exit()

    logging.info("Starting ARM processing at " + str(datetime.datetime.now()))

    log_udev_params()
    # log_arm_params(disc)

    try:
        main(logfile, disc)
    except Exception:
        logging.exception("A fatal error has occured and ARM is exiting.  See traceback below for details.")
