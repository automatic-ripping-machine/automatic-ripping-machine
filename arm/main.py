#!/usr/bin/python3

import sys
import argparse
import os
import logging
import time
import datetime
import shutil
import pyudev
import logger
import utils
import makemkv
import handbrake
# import classes
import identify

from config import cfg
from classes import Disc

# from config import cfg

def entry():
    """ Entry to program, parses arguments"""
    parser = argparse.ArgumentParser(description='Process disc using ARM')
    parser.add_argument('-d', '--devpath', help='Devpath', required=True)

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
    logging.info("hb_preset_dvd: " + cfg['HB_PRESET_DVD'])
    logging.info("hb_preset_bd: " + cfg['HB_PRESET_BD'])
    logging.info("hb_args_dvd: " + cfg['HB_ARGS_DVD'])
    logging.info("hb_args_bd: " + cfg['HB_ARGS_BD'])
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

    utils.notify("ARM notification", "Found disc: " + str(disc.videotitle) + ". Video type is " + str(disc.videotype) + ". Main Feature is " + cfg['MAINFEATURE'] + ".")

    #get filesystem in order
    hboutpath = os.path.join(cfg['ARMPATH'], str(disc.videotitle))

    if (utils.make_dir(hboutpath)) is False:
        ts = round(time.time() * 100)
        hboutpath = os.path.join(cfg['ARMPATH'], str(disc.videotitle) + "_" + str(ts))
        if(utils.make_dir(hboutpath)) is False:
            logging.info("Failed to create base directory.  Exiting.")
            sys.exit()
    
    logging.info("Processing files to: " + hboutpath)
    
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
        handbrake.handbrake_mainfeature(hbinpath, hboutpath, logfile, disc)
        os.system("eject " + disc.devpath)
    else:
        handbrake.handbrake_all(hbinpath, hboutpath, logfile, disc)
        os.system("eject " + disc.devpath)

    if disc.disctype == "bluray":
        shutil.rmtree(mkvoutpath)

    if disc.errors:
        errlist = ', '.join(disc.errors)
        utils.notify("ARM notification", str(disc.videotitle) + " processing completed with errors. Title(s) " + errlist + " failed to complete.")
        logging.info("Transcoding comleted with errors.  Title(s) " + errlist + " failed to complete.")
    else:
        utils.notify("ARM notification", str(disc.videotitle) + " processing complete.")
        logging.info("Transcoding comlete")

    

if __name__ == "__main__":
    args = entry()

    devpath = "/dev/" + args.devpath
    print(devpath)

    disc = Disc(devpath)
    print (disc.label)

    logfile = logger.setuplogging(disc)

    logger.cleanuplogs(cfg['LOGPATH'], cfg['LOGLIFE'])

    if disc.label == "":
        logging.info("Drive appears to be empty.  Exiting ARM.")
        sys.exit()

    logging.info("Starting ARM processing at " + str(datetime.datetime.now()))

    log_udev_params()

    try:
        main(logfile, disc)
    except Exception:
        logging.exception("A fatal error has occured and ARM is exiting.  See traceback below for details.")
        utils.notify("ARM notification", "ARM encountered a fatal error processing " + str(disc.videotitle) + ". Check the logs for more details")
