#!/usr/bin/python3

import os
import sys # noqa # pylint: disable=unused-import
import logging
#import classes # noqa # pylint: disable=unused-import
#import ripper.getmovietitle
#import ripper.getvideotype
#import ripper.utils

from ripper import getmovietitle, getvideotype, utils
from config.config import cfg


def identify(job, logfile):
    """Identify disc attributes"""

    logging.debug("Identification starting: " + str(job))

    # If UDF CHeck is on
    # if cfg['ARM_CHECK_UDF']:

    logging.info("Mounting disc to: " + str(job.mountpoint))

    if not os.path.exists(str(job.mountpoint)):
        os.makedirs(str(job.mountpoint))

    os.system("mount " + job.devpath)

    # Check to make sure it's not a data disc
    if job.disctype == "music":
        logging.debug("Disc is music.  Skipping identification")
    elif os.path.isdir(job.mountpoint + "/VIDEO_TS"):
        logging.debug("Found: " + job.mountpoint + "/VIDEO_TS")
        job.disctype = "dvd"
    elif os.path.isdir(job.mountpoint + "/video_ts"):
        logging.debug("Found: " + job.mountpoint + "/video_ts")
        job.disctype = "dvd"
    elif os.path.isdir(job.mountpoint + "/BDMV"):
        logging.debug("Found: " + job.mountpoint + "/BDMV")
        job.disctype = "bluray"
    elif os.path.isdir(job.mountpoint + "/HVDVD_TS"):
        logging.debug("Found: " + job.mountpoint + "/HVDVD_TS")
        # do something here
    elif utils.find_file("HVDVD_TS", job.mountpoint):
        logging.debug("Found file: HVDVD_TS")
        # do something here too
    else:
        logging.debug("Did not find valid dvd/bd files. Changing disctype to 'data'")
        job.disctype = "data"

    if job.disctype in ["dvd", "bluray"]:

        logging.info("Disc identified as video")

        if cfg["GET_VIDEO_TITLE"]:

            logging.info("Getting movie title...")
            job.title, job.videoyear = getmovietitle.main(job)

            if job.hasnicetitle:
                logging.info("Getting video type...")
                job.videotype, job.videoyear = getvideotype.main(job)
            else:
                logging.info("Disc does not have a nice title.  Skipping video type identification and setting title=title_unkonwn")
                job.title = "title_unknown"

            if not cfg['VIDEOTYPE'].lower() == "auto":
                logging.debug("Overriding videotype with value in VIDEOTYPE config parameter: " + cfg['VIDEOTYPE'].lower())
                job.videotype = cfg['VIDEOTYPE'].lower()

            logging.info("Disc title: " + str(job.title) + " : " + str(job.videoyear) + " : " + str(job.videotype))
            logging.debug("Identification complete: " + str(job))

    os.system("umount " + job.devpath)
