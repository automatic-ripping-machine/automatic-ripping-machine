#!/usr/bin/python3

import os
import sys
import logging
import classes
import getmovietitle
import getvideotype
import utils

from config import cfg

def identify(disc, logfile):
    """Identify disc attributes"""

    logging.debug("Identification starting: " + str(disc))

    #If UDF CHeck is on
    # if cfg['ARM_CHECK_UDF']:

    logging.info("Mounting disc to: " + str(disc.mountpoint))

    if not os.path.exists(str(disc.mountpoint)):
        os.makedirs(str(disc.mountpoint))

    os.system("mount " + disc.devpath)

    # Check to make sure it's not a data disc
    if os.path.isdir(disc.mountpoint + "/VIDEO_TS"):
        logging.debug("Found: " + disc.mountpoint + "/VIDEO_TS")
    elif os.path.isdir(disc.mountpoint + "/BDMV"):
        logging.debug("Found: " + disc.mountpoint + "/BDMV")
    elif os.path.isdir(disc.mountpoint + "/HVDVD_TS"):
        logging.debug("Found: " + disc.mountpoint + "/HVDVD_TS")
    elif utils.find_file("HVDVD_TS", disc.mountpoint):
        logging.debug("Found file: HVDVD_TS")
    else:
        logging.debug("Did not find valid dvd/bd files. Changing disctype to 'data'")
        disc.disctype = "data"

    if disc.disctype in ["dvd", "bluray"]:
        
        logging.info("Disc identified as video")

        if str(cfg["GET_VIDEO_TITLE"]).lower == "true":

            logging.info("Getting movie title...")
            disc.videotitle, disc.videoyear = getmovietitle.main(disc)

            logging.info("Getting video type...")
            disc.videotype, disc.videoyear = getvideotype.main(disc)

            logging.info("Disc title: " + str(disc.videotitle) + " : " + str(disc.videoyear) + " : " + str(disc.videotype))
            logging.debug("Identification complete: " + str(disc))

    os.system("umount " + disc.devpath)
