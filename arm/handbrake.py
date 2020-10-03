#!/usr/bin/python3

import sys
import os
import logging
import subprocess
import re
import shlex
import utils

from config import cfg


def handbrake_mainfeature(srcpath, basepath, logfile, disc):
    """process dvd with mainfeature enabled.\n
    srcpath = Path to source for HB (dvd or files)\n
    basepath = Path where HB will save trancoded files\n
    logfile = Logfile for HB to redirect output to\n
    disc = Disc object\n

    Returns nothing
    """
    logging.info("Starting DVD Movie Mainfeature processing")

    filename = os.path.join(basepath, disc.videotitle + ".mkv")
    filepathname = os.path.join(basepath, filename)

    logging.info("Ripping title Mainfeature to " + shlex.quote(filepathname))

    if disc.disctype == "dvd":
        hb_args = cfg['HB_ARGS_DVD']
        hb_preset = cfg['HB_PRESET_DVD']
    elif disc.disctype == "bluray":
        hb_args = cfg['HB_ARGS_BD']
        hb_preset = cfg['HB_PRESET_BD']

    cmd = 'nice {0} -i {1} -o {2} --main-feature --preset "{3}" {4} >> {5} 2>&1'.format(
        cfg['HANDBRAKE_CLI'],
        shlex.quote(srcpath),
        shlex.quote(filepathname),
        hb_preset,
        hb_args,
        logfile
        )

    logging.debug("Sending command: %s", (cmd))

    try:
        subprocess.check_output(
            cmd,
            shell=True
        ).decode("utf-8")
        logging.info("Handbrake call successful")
    except subprocess.CalledProcessError as hb_error:
        err = "Call to handbrake failed with code: " + str(hb_error.returncode) + "(" + str(hb_error.output) + ")"
        logging.error(err)
        sys.exit(err)

    logging.info("Handbrake processing complete")
    logging.debug(str(disc))
    utils.move_files(basepath, filename, disc.hasnicetitle, disc.videotitle + " (" + disc.videoyear + ")", True)
    utils.scan_emby()

    try:
        os.rmdir(basepath)
    except OSError:
        pass


def handbrake_all(srcpath, basepath, logfile, disc):
    """Process all titles on the dvd\n
    srcpath = Path to source for HB (dvd or files)\n
    basepath = Path where HB will save trancoded files\n
    logfile = Logfile for HB to redirect output to\n
    disc = Disc object\n

    Returns nothing
    """
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
    for line in hb.stderr.decode(errors='ignore').splitlines(True):
        # get number of titles on disc
        # pattern = re.compile(r'\bscan\:.*\btitle\(s\)')

        if disc.disctype == "bluray":
            result = re.search(r'scan: BD has (.*) title\(s\)', line)
        else:
            result = re.search(r'scan: DVD has (.*) title\(s\)', line)

        if result:
            titles = result.group(1)
            titles = titles.strip()
            logging.debug("Line found is: " + line)
            logging.info("Found " + titles + " titles")

        # get main feature title number
        if(re.search("Main Feature", line)) is not None:
            t = prevline.split()
            mt_track = re.sub('[:]', '', (t[2]))
            logging.debug("Lines found are: 1) " + line.rstrip() + " | 2)" + prevline)
            logging.info("Main Feature is title #" + mt_track)
        prevline = line

    if titles == 0:
        raise ValueError("Couldn't get total number of tracks", "handbrake_all")

    mt_track = str(mt_track).strip()

    if disc.disctype == "dvd":
        hb_args = cfg['HB_ARGS_DVD']
        hb_preset = cfg['HB_PRESET_DVD']
    elif disc.disctype == "bluray":
        hb_args = cfg['HB_ARGS_BD']
        hb_preset = cfg['HB_PRESET_BD']

    for title in range(1, int(titles) + 1):

        # get length
        tlength = get_title_length(title, srcpath)

        if tlength < int(cfg['MINLENGTH']):
            # too short
            logging.info("Track #" + str(title) + " of " + str(titles) + ". Length (" + str(tlength) +
                         ") is less than minimum length (" + cfg['MINLENGTH'] + ").  Skipping")
        elif tlength > int(cfg['MAXLENGTH']):
            # too long
            logging.info("Track #" + str(title) + " of " + str(titles) + ". Length (" + str(tlength) +
                         ") is greater than maximum length (" + cfg['MAXLENGTH'] + ").  Skipping")
        else:
            # just right
            logging.info("Processing track #" + str(title) + " of " + str(titles) + ". Length is " + str(tlength) + " seconds.")

            filename = "title_" + str.zfill(str(title), 2) + "." + cfg['DEST_EXT']
            filepathname = os.path.join(basepath, filename)

            logging.info("Transcoding title " + str(title) + " to " + shlex.quote(filepathname))

            cmd = 'nice {0} -i {1} -o {2} --preset "{3}" -t {4} {5}>> {6} 2>&1'.format(
                cfg['HANDBRAKE_CLI'],
                shlex.quote(srcpath),
                shlex.quote(filepathname),
                hb_preset,
                str(title),
                hb_args,
                logfile
                )

            logging.debug("Sending command: %s", (cmd))

            try:
                hb = subprocess.check_output(
                    cmd,
                    shell=True
                ).decode("utf-8")
                logging.debug("Handbrake exit code: " + hb)
            except subprocess.CalledProcessError as hb_error:
                err = "Handbrake encoding of title " + str(title) + " failed with code: " + str(hb_error.returncode) + "(" + str(hb_error.output) + ")"
                logging.error(err)
                disc.errors.append(str(title))
                # return
                # sys.exit(err)

            # move file
            if disc.videotype == "movie":
                logging.debug("mt_track: " + mt_track + " List track: " + str(title))
                if mt_track == str(title):
                    utils.move_files(basepath, filename, disc.hasnicetitle, disc.videotitle + " (" + disc.videoyear + ")", True)
                else:
                    utils.move_files(basepath, filename, disc.hasnicetitle, disc.videotitle + " (" + disc.videoyear + ")", False)

    logging.info("Handbrake processing complete")
    logging.debug(str(disc))
    if disc.videotype == "movie" and disc.hasnicetitle:
        utils.scan_emby()
        try:
            os.rmdir(basepath)
        except OSError:
            pass


def handbrake_mkv(srcpath, basepath, logfile, disc):
    """process all mkv files in a directory.\n
    srcpath = Path to source for HB (dvd or files)\n
    basepath = Path where HB will save trancoded files\n
    logfile = Logfile for HB to redirect output to\n
    disc = Disc object\n

    Returns nothing
    """

    if disc.disctype == "dvd":
        hb_args = cfg['HB_ARGS_DVD']
        hb_preset = cfg['HB_PRESET_DVD']
    elif disc.disctype == "bluray":
        hb_args = cfg['HB_ARGS_BD']
        hb_preset = cfg['HB_PRESET_BD']

    for f in os.listdir(srcpath):
        srcpathname = os.path.join(srcpath, f)
        destfile = os.path.splitext(f)[0]
        filename = os.path.join(basepath, destfile + "." + cfg['DEST_EXT'])
        filepathname = os.path.join(basepath, filename)

        logging.info("Transcoding file " + shlex.quote(f) + " to " + shlex.quote(filepathname))

        cmd = 'nice {0} -i {1} -o {2} --preset "{3}" {4}>> {5} 2>&1'.format(
            cfg['HANDBRAKE_CLI'],
            shlex.quote(srcpathname),
            shlex.quote(filepathname),
            hb_preset,
            hb_args,
            logfile
            )

        logging.debug("Sending command: %s", (cmd))

        try:
            hb = subprocess.check_output(
                cmd,
                shell=True
            ).decode("utf-8")
            logging.debug("Handbrake exit code: " + hb)
        except subprocess.CalledProcessError as hb_error:
            err = "Handbrake encoding of file " + shlex.quote(f) + " failed with code: " + str(hb_error.returncode) + "(" + str(hb_error.output) + ")"
            logging.error(err)
            disc.errors.append(f)

    logging.info("Handbrake processing complete")
    logging.debug(str(disc))


def get_title_length(title, srcpath):
    """Use HandBrake to get the title length\n
    title = title to scan\n
    srcpath = location of the dvd or decrypted bluray\n

    returns the length of the title or -1 if the length could not be determinied
    """
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
    except subprocess.CalledProcessError:
        # err = "Call to handbrake failed with code: " + str(hb_error.returncode) + "(" + str(hb_error.output) + ")"
        logging.debug("Couldn't find a valid track.  Try running the command manually to see more specific errors.")
        return(-1)
        # sys.exit(err)

    pattern = re.compile(r'.*duration\:.*')
    for line in hb:
        if(re.search(pattern, line)) is not None:
            t = line.split()
            h, m, s = t[2].split(':')
            seconds = int(h) * 3600 + int(m) * 60 + int(s)
            return(seconds)
