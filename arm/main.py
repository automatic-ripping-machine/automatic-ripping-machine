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
    # logging.info("plex_support: " + cfg['PLEX_SUPPORT'])
    logging.info("emby_subfolders: " + cfg['EMBY_SUBFOLDERS'])
    logging.info("emby_server: " + cfg['EMBY_SERVER'])
    logging.info("emby_port: " + cfg['EMBY_PORT'])
    logging.info("*** End of dvd parameters ***")

# def scan_emby():
#     """Trigger a media scan on Emby"""

#     logging.info("Sending Emby library scan request")
#     url = "http://" + cfg['EMBY_SERVER'] + ":" + cfg['EMBY_PORT'] + "/Library/Refresh?api_key=" + cfg['EMBY_API_KEY']
#     try:
#         req = requests.post(url)
#         if req.status_code > 299:
#             req.raise_for_status()
#         logging.info("Emby Library Scan request successful")
#     except requests.exceptions.HTTPError:
#         logging.error("Emby Library Scan request failed with status code: " + str(req.status_code))

# def move_files(basepath, filename, hasnicetitle, videotitle, ismainfeature=False):
#     """Move files into final media directory
#     basepath = path to source directory
#     filename = name of file to be moved
#     hasnicetitle = hasnicetitle value
#     ismainfeature = True/False"""

#     logging.debug("Arguments: " + basepath + " : " + filename + " : " + hasnicetitle + " : " + str(ismainfeature))

#     if hasnicetitle == "true":
#         m_path = os.path.join(cfg['MEDIA_DIR'] + videotitle)

#         if not os.path.exists(m_path):
#             logging.info("Creating base title directory: " + m_path)
#             os.makedirs(m_path)

#         if ismainfeature is True:
#             logging.info("Track is the Main Title.  Moving '" + filename + "' to " + m_path)

#             try:
#                 shutil.move(os.path.join(basepath, filename), os.path.join(m_path, videotitle + "." + cfg['DEST_EXT']))
#             except shutil.Error:
#                 logging.error("Unable to move '" + filename + "' to " + m_path)
#         else:
#             e_path = os.path.join(m_path, "extras")

#             logging.info("Creating extras directory " + e_path)
#             if not os.path.exists(e_path):
#                 os.makedirs(e_path)

#             logging.info("Moving '" + filename + "' to " + e_path)

#             try:
#                 shutil.move(os.path.join(basepath, filename), os.path.join(e_path, filename))
#             except shutil.Error:
#                 logging.error("Unable to move '" + filename + "' to " + e_path)

#     else:
#         logging.info("hasnicetitle is false.  Not moving files.")

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
