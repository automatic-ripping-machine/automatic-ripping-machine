#!/usr/bin/python3

import sys
import os
import logging
import subprocess
import re
import shlex
import requests
import argparse
import time
import logger
import main
import utils

from config import cfg

def handbrake_mainfeature(srcpath, basepath, videotitle, logfile, hasnicetitle):
    """process dvd with mainfeature enabled"""
    logging.info("Starting DVD Movie Mainfeature processing")

    filename = os.path.join(basepath, videotitle + ".mkv")
    filepathname = os.path.join(basepath, filename)

    logging.info("Ripping title Mainfeature to " + shlex.quote(filepathname))

    cmd = 'nice {0} -i {1} -o {2} --main-feature --preset "{3}" {4}'.format(
        cfg['HANDBRAKE_CLI'],
        shlex.quote(srcpath),
        shlex.quote(filepathname),
        cfg['HB_PRESET'],
        cfg['HB_ARGS']
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
        sys.exit(err)

    utils.move_files(basepath, filename, hasnicetitle, videotitle, True)
    utils.scan_emby()

    try:
        os.rmdir(basepath)
    except OSError:
        pass

def handbrake_all(srcpath, basepath, videotitle, logfile, hasnicetitle, videotype):
    """Process all titles on the dvd"""
    logging.info("Starting BluRay/DVD transcoding - All titles")

    # get number of titles
    logging.info("Getting total number of titles on disc.  This will take a minute or two...")
    cmd = '{0} -i {1} -t 0 --scan'.format(
        cfg['HANDBRAKE_CLI'],
        shlex.quote(srcpath)
        )

    logging.debug("Sending command: %s", (cmd))

    try:
        hb = subprocess.run(
            cmd,
            stderr=subprocess.PIPE,
            shell=True
        )
    except subprocess.CalledProcessError as hb_error:
        err = "Call to handbrake failed with code: " + str(hb_error.returncode) + "(" + str(hb_error.output) + ")"
        logging.error(err)
        sys.exit(err)

    titles = 0
    mt_track = 0
    prevline = ""
    for line in hb.stderr.decode("utf-8").splitlines():
        # get number of titles on disc
        pattern = re.compile(r'\bscan\:.*\btitle\(s\)')
        if(re.search(pattern, line)) != None:
            t = line.split()
            titles = (t[4])
            logging.debug("Line found is: " + line)
            logging.info("Found " + titles.strip() + " titles")

        # get main feature title number
        if(re.search("Main Feature", line)) != None:
            t = prevline.split()
            mt_track = re.sub('[:]', '', (t[2]))
            logging.debug("Line found is: " + line)
            logging.info("Main Feature is title #" + mt_track)
        prevline = line

    if titles == 0:
        raise ValueError("Couldn't get total number of tracks","handbrake_all")

    mt_track = str(mt_track).strip()

    for title in range(1, int(titles) + 1):
        
        # get length
        tlength = get_title_length(title, srcpath)
        
        if tlength < int(cfg['MINLENGTH']):
            #too short
            logging.info("Track #" + str(title) + " of " + str(titles) + ". Length (" + str(tlength) + \
            ") is less than minimum length (" + cfg['MINLENGTH'] + ").  Skipping")
        elif tlength > int(cfg['MAXLENGTH']):
            #too long
            logging.info("Track #" + str(title) +" of " + str(titles) + ". Length (" + str(tlength) + \
            ") is greater than maximum length (" + cfg['MAXLENGTH'] + ").  Skipping")
        else:
            #just right
            logging.info("Processing track #" + str(title) + " of " + str(titles) + ". Length is " + str(tlength) + " seconds.")

            filename = "title_" + str.zfill(str(title), 2) + "." + cfg['DEST_EXT']
            filepathname = os.path.join(basepath, filename)

            logging.info("Transcoding title " + str(title) + " to " + shlex.quote(filepathname))

            cmd = 'nice {0} -i "{1}" -o {2} --preset "{3}" -t {4} {5}>> {6}'.format(
                cfg['HANDBRAKE_CLI'],
                shlex.quote(srcpath),
                shlex.quote(filepathname),
                cfg['HB_PRESET'],
                str(title),
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
            if videotype == "movie":
                logging.debug("mt_track: " + mt_track + " List track: " + str(title))
                if mt_track == str(title):
                    utils.move_files(basepath, filename, hasnicetitle, videotitle, True)
                else:
                    utils.move_files(basepath, filename, hasnicetitle, videotitle, False)

    if videotype == "movie" and hasnicetitle:
        utils.scan_emby()

    try:
        os.rmdir(basepath)
    except OSError:
        pass


def get_title_length(title, srcpath):
    """process all titles on disc""" 
    logging.debug("Getting length from " + srcpath + " on title: " + str(title))

    cmd = '{0} -i {1} -t {2} --scan'.format(
        cfg['HANDBRAKE_CLI'],
        shlex.quote(srcpath),
        title
        )

    logging.debug("Sending command: %s", (cmd))

    try:
        hb = subprocess.check_output(
            cmd,
            stderr=subprocess.STDOUT,
            shell=True
        ).decode("utf-8").splitlines()
    except subprocess.CalledProcessError as hb_error:
        # err = "Call to handbrake failed with code: " + str(hb_error.returncode) + "(" + str(hb_error.output) + ")"
        logging.debug("Couldn't find a valid track.  Try running the command manually to see more specific errors.")
        return(-1)
        # sys.exit(err)


    pattern = re.compile(r'.*duration\:.*')
    for line in hb:
        if(re.search(pattern, line)) != None:
            t = line.split()
            h, m, s = t[2].split(':')
            seconds =  int(h) * 3600 + int(m) * 60 + int(s)
            return(seconds)


