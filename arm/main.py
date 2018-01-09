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
import utils
import makemkv
import handbrake

from config import cfg

def entry():
    """ Entry to program, parses arguments"""
    parser = argparse.ArgumentParser(description='Process DVD using HandBrakeCLI')
    parser.add_argument('-d', '--devpath', help='Devpath', required=True)
    parser.add_argument('-t', '--videotitle', help='Video Title', required=True)
    parser.add_argument('-y', '--videotype', help='Video Type', required=True)
    parser.add_argument('-e', '--label', help='Label', required=True)
    parser.add_argument('-n', '--hasnicetitle', help="Has Nice Title", required=False)
    parser.add_argument('-b', '--isbluray', help="Is Bluray", default="false", required=False)


    return parser.parse_args()

def log_params(logfile):
    """log all entry parameters"""

    logging.info("Logging dvd parameters")
    logging.info("**** Start tv_dvd.py paramaters *** ")
    logging.info("devpath: " + args.devpath)
    logging.info("videotitle: " + args.videotitle)
    logging.info("mainfeature: " + cfg['MAINFEATURE'])
    logging.info("videotype: " + args.videotype)
    logging.info("minlength: " + cfg['MINLENGTH'])
    logging.info("maxlength: " + cfg['MAXLENGTH'])
    logging.info("hb_preset: " + cfg['HB_PRESET'])
    logging.info("hb_args: " + cfg['HB_ARGS'])
    logging.info("logfile: " + logfile)
    logging.info("hasnicetitle: " + args.hasnicetitle)
    logging.info("media_dir: " + cfg['MEDIA_DIR'])
    logging.info("extras_sub" + cfg['EXTRAS_SUB'])
    logging.info("isbluray: " + args.isbluray)
    logging.info("emby_refresh: " + cfg['EMBY_REFRESH'])
    logging.info("emby_subfolders: " + cfg['EMBY_SUBFOLDERS'])
    logging.info("emby_server: " + cfg['EMBY_SERVER'])
    logging.info("emby_port: " + cfg['EMBY_PORT'])
    logging.info("*** End of dvd parameters ***")

def main(logfile):
    """main dvd processing function"""
    logging.info("Starting Disc processing")

    utils.notify("ARM notification", "Found disc: " + args.videotitle + ". Video type is " + args.videotype + ". Main Feature is " + cfg['MAINFEATURE'] + ".")

    #get filesystem in order
    basepath = os.path.join(cfg['ARMPATH'], args.videotitle)

    if not os.path.exists(basepath):
        try:
            os.makedirs(basepath)
        except OSError:
            logging.error("Couldn't create the base file path: " + basepath + " Probably a permissions error")
            err = "Couldn't create the base file path: " + basepath + " Probably a permissions error"
            sys.exit(err)
    else:
        ts = round(time.time() * 100)
        basepath = os.path.join(cfg['ARMPATH'], args.videotitle + "_" + str(ts))
        try:
            os.makedirs(basepath)
        except OSError:
            logging.error("Couldn't create the base file path: " + basepath + " Probably a permissions error")
            err = "Couldn't create the base file path: " + basepath + " Probably a permissions error"
            sys.exit(err)

    if args.isbluray == "true":
        #send to makemkv for ripping
        if cfg['RIPMETHOD'] == "backup":
            #backup method
            src = makemkv.makemkv(logfile, args.devpath, args.videotitle)
            args.devpath = src
        # else:
            #currently do nothing

    if args.videotype == "movie" and cfg['MAINFEATURE'] == "true":
        handbrake.handbrake_mainfeature(args.devpath, basepath, args.videotitle, logfile, args.hasnicetitle)
    else:
        # handbrake_all(basepath, logfile)
        handbrake.handbrake_all(args.devpath, basepath, args.videotitle, logfile, args.hasnicetitle, args.videotype)

    if args.isbluray == "true":
        shutil.rmtree(src)

    utils.notify("ARM notification", "DVD: " + args.videotitle + "processing complete.")

    logging.info("Transcoding comlete")

if __name__ == "__main__":
    args = entry()

    logfile = logger.setuplogging()

    log_params(logfile)

    main(logfile)
