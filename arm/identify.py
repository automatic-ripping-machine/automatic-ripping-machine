#!/usr/bin/python3

import os
import sys
import logging
import classes
import getmovietitle
import getvideotype

from config import cfg

def identify(disc):
    """Identify disc attributes"""

    #If UDF CHeck is on
    if cfg['ARM_CHECK_UDF']:
        #check if it's a video
        # mountpoint = "/mnt" + str(disc.devpath)
        logging.debug("Identification starting: " + str(disc))
        
        logging.info("Mounting disc to: " + str(disc.mountpoint))

        if not os.path.exists(str(disc.mountpoint)):
            os.makedirs(str(disc.mountpoint))

        # os.system("mount " + disc.devpath + " " + disc.mountpoint)
        os.system("mount " + disc.devpath)

        logging.info("Getting movie title...")
        disc.videotitle, disc.videoyear = getmovietitle.main(disc)

        logging.info("Getting video type...")
        disc.videotype, disc.videoyear = getvideotype.main(disc)

        os.system("umount " + disc.devpath

        logging.info("Disc title: " + str(disc.videotitle) + " : " + str(disc.videoyear) + " : " + str(disc.videotype))
        logging.debug("Identification complete: " + str(disc))

        # if cfg['GET_VIDEO_TITLE']:

    else:
        pass