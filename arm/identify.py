#!/usr/bin/python3

import os
import sys
import logging
import classes
import getmovietitle
import getvideotype

from config import cfg

def identify(disc, logfile):
    """Identify disc attributes"""

    logging.debug("Identification starting: " + str(disc))

    #If UDF CHeck is on
    # if cfg['ARM_CHECK_UDF']:
    if disc.disctype in ["dvd", "bluray"]: 
        #check if it's a video
        # mountpoint = "/mnt" + str(disc.devpath)
        
        logging.info("Mounting disc to: " + str(disc.mountpoint))

        if not os.path.exists(str(disc.mountpoint)):
            os.makedirs(str(disc.mountpoint))

        # os.system("mount " + disc.devpath + " " + disc.mountpoint)
        os.system("mount " + disc.devpath)

        ###### do udf check here if needed #####
        logging.info("Disc identified as video")

        logging.info("Getting movie title...")
        disc.videotitle, disc.videoyear = getmovietitle.main(disc)

        logging.info("Getting video type...")
        disc.videotype, disc.videoyear = getvideotype.main(disc)

        os.system("umount " + disc.devpath)

        logging.info("Disc title: " + str(disc.videotitle) + " : " + str(disc.videoyear) + " : " + str(disc.videotype))
        logging.debug("Identification complete: " + str(disc))

    else:
        # logging.info("Couldn't identify the disc type. Exiting without any action.")
        pass