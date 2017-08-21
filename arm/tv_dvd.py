#!/usr/bin/python3

import sys
import argparse
import os
import subprocess
import logging
import time
import shutil
import requests
import logger
import notify

from config import cfg

def entry():
    """ Entry to program, parses arguments"""
    parser = argparse.ArgumentParser(description='Process DVD using HandBrakeCLI')
    parser.add_argument('-d', '--devpath', help='Devpath', required=True)
    parser.add_argument('-t', '--videotitle', help='Video Title', required=True)
    parser.add_argument('-y', '--videotype', help='Video Type', required=True)
    parser.add_argument('-e', '--label', help='Label', required=True)
    parser.add_argument('-n', '--hasnicetitle', help="Has Nice Title", required=False)


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
    logging.info("MEDIA_DIR: " + cfg['MEDIA_DIR'])
    logging.info("*** End of dvd parameters ***")

def handbrake_mainfeature(basepath, logfile):
    """process dvd with mainfeature enabled"""
    logging.info("Starting DVD Movie Mainfeature processing")

    filename = os.path.join(basepath, args.videotitle + ".mkv")
    filepathname = os.path.join(basepath, filename)

    logging.info("Ripping title Mainfeature to " + filepathname)

    cmd = 'nice {0} -i "{1}" -o "{2}" --main-feature --preset "{3}" {4}>> {5}'.format(
        cfg['HANDBRAKE_CLI'],
        args.devpath,
        filepathname,
        cfg['HB_PRESET'],
        cfg['HB_ARGS'],
        logfile
        )

    logging.debug("Sending command: %s", (cmd))

    try:
        hb = subprocess.check_output(
            cmd,
            shell=True
        ).decode("utf-8")
    except subprocess.CalledProcessError as hb_error:
        err = "Call to hadnbrake failed with code: " + str(hb_error.returncode) + "(" + str(hb_error.output) + ")"
        logging.error(err)
        sys.exit(err)

    move_files(basepath, filename, True)

    try:
        os.rmdir(basepath)
    except OSError:
        pass
        
    scan_emby()

def handbrake_all(basepath, logfile):
    """Process all titles on the dvd"""

    # get title info
    try:
        d = subprocess.check_output(["lsdvd", '-Oy', args.devpath]).decode("utf-8")
    except subprocess.CalledProcessError as derror:
        print("Call to lsdvd failed with code: " + str(derror.returncode), derror.output)
        err = "Aborting.  Call to lsdvd failed with code: " + str(derror.returncode), derror.output
        sys.exit(err)

    data = d.replace("lsdvd = ", "", 1)
    info = eval(data, {})
    # print(info['track'])

    total = 0
    for index, item in enumerate(info['track']):
        if item['ix'] > total:
            total = item['ix']

    logging.info("Found " + str(total) + " tracks.")

    #check for main title
    cmd = '{0} --input "{1}" --title 0 --scan |& grep -B 1 "Main Feature" | sed \'s/[^0-9]*//g\''.format(
        cfg['HANDBRAKE_CLI'],
        args.devpath
        )

    # Get main title track #
    if args.hasnicetitle == "true":
        try:
            mt_track = subprocess.check_output(
                cmd,
                executable="/bin/bash",
                shell=True
            ).decode("utf-8")
            logging.info("Maintitle track is #" + mt_track)
        except subprocess.CalledProcessError as mt_error:
            err = "Attempt to retrieve maintitle track number from Handbrake failed with code: " + str(mt_error.returncode) + "(" + str(mt_error.output) + ")"
            logging.error(err)
    else:
        mt_track = 0

        mt_track = str(mt_track).strip()

    for index, item in enumerate(info['track']):
        if item['length'] < int(cfg['MINLENGTH']):
            #too short
            logging.info("Track #" + str(item['ix']) + " of " + str(total) + ". Length (" + str(item['length']) + \
            ") is less than minimum length (" + cfg['MINLENGTH'] + ").  Skipping")
        elif item['length'] > int(cfg['MAXLENGTH']):
            #too long
            logging.info("Track #" + str(item['ix']) +" of " + str(total) + ". Length (" + str(item['length']) + \
            ") is greater than maximum length (" + cfg['MAXLENGTH'] + ").  Skipping")
        else:
            #just right
            logging.info("Processing track #" + str(item['ix']) + " of " + str(total) + ". Length is " + str(item['length']) + " seconds.")

            filename = "title_" + str.zfill(str((item['ix'])), 2) + "." + cfg['DEST_EXT']
            filepathname = os.path.join(basepath, filename)

            logging.info("Ripping title " + str((item['ix'])) + " to " + filepathname)

            cmd = 'nice {0} -i "{1}" -o "{2}" --preset "{3}" -t {4} {5}>> {6}'.format(
                cfg['HANDBRAKE_CLI'],
                args.devpath,
                filepathname,
                cfg['HB_PRESET'],
                str(item['ix']),
                cfg['HB_ARGS'],
                logfile
                )

            logging.debug("Sending command: %s", (cmd))

            try:
                hb = subprocess.check_output(
                    cmd,
                    shell=True
                ).decode("utf-8")
            except subprocess.CalledProcessError as hb_error:
                err = "Call to handbrake failed with code: " + str(hb_error.returncode) + "(" + str(hb_error.output) + ")"
                logging.error(err)
                return
                # sys.exit(err)

            # move file
            if args.videotype == "movie":
                if mt_track == str(item['ix']):
                    move_files(basepath, filename, True)
                else:
                    move_files(basepath, filename, False)

    try:
        os.rmdir(basepath)
    except OSError:
        pass

    scan_emby()


def scan_emby():
    """Trigger a media scan on Emby"""

    logging.info("Sending Emby library scan request")
    url = "http://" + cfg['EMBY_SERVER'] + ":" + cfg['EMBY_PORT'] + "/Library/Refresh?api_key=" + cfg['EMBY_API_KEY']
    try:
        req = requests.post(url)
        if req.status_code > 299:
            req.raise_for_status()
        logging.info("Emby Library Scan request successful")
    except requests.exceptions.HTTPError:
        logging.error("Emby Library Scan request failed with status code: " + str(req.status_code))

def move_files(basepath, filename, ismainfeature=False):
    """Move files into final media directory
    basepath = path to source directory
    filename = name of file to be moved
    ismainfeature = True/False"""

    logging.debug("Arguments: " + basepath + " : " + filename + " : " + str(ismainfeature))

    if args.hasnicetitle == "true":
        m_path = os.path.join(cfg['MEDIA_DIR'] + args.videotitle)

        if not os.path.exists(m_path):
            logging.info("Creating base title directory: " + m_path)
            os.makedirs(m_path)

        if ismainfeature is True:
            logging.info("Track is the Main Title.  Moving '" + filename + "' to " + m_path)

            try:
                shutil.move(os.path.join(basepath, filename), os.path.join(m_path, args.videotitle + "." + cfg['DEST_EXT']))
            except shutil.Error:
                logging.error("Unable to move '" + filename + "' to " + m_path)
        else:
            e_path = os.path.join(m_path, "extras")

            logging.info("Creating extras directory " + e_path)
            if not os.path.exists(e_path):
                os.makedirs(e_path)

            logging.info("Moving '" + filename + "' to " + e_path)

            try:
                shutil.move(os.path.join(basepath, filename), os.path.join(e_path, filename))
            except shutil.Error:
                logging.error("Unable to move '" + filename + "' to " + e_path)

    else:
        logging.info("hasnicetitle is false.  Not moving files.")

def main(logfile):
    """main dvd processing function"""
    logging.info("Starting DVD processing")

    notify.notify("ARM notification","Found disc: " + args.videotitle + ". Video type is " + args.videotype + ". Main Feature is " + cfg['MAINFEATURE'] + ".")

    #get filesystem in order
    ts = round(time.time() * 100)
    basepath = os.path.join(cfg['ARMPATH'], args.label + "_" + str(ts))

    if not os.path.exists(basepath):
        try:
            os.makedirs(basepath)
        except OSError:
            logging.error("Couldn't create the base file path: " + basepath + " Probably a permissions error")
            err = "Couldn't create the base file path: " + basepath + " Probably a permissions error"
            sys.exit(err)

    if args.videotype == "movie" and cfg['MAINFEATURE'] == "true":
        handbrake_mainfeature(basepath, logfile)
    else:
        handbrake_all(basepath, logfile)

    notify.notify("ARM notification", "DVD: " + args.videotitle + "processing complete.")

    logging.info("DVD processing comlete")


args = entry()

#set up logging
# logging.basicConfig(filename=args.logfile, format='[%(asctime)s] ARM: %(levelname)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S', \
# level=logging.INFO)
logfile = logger.setuplogging()

log_params(logfile)

main(logfile)
