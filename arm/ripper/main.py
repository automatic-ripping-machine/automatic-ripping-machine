#!/usr/bin/python3

import sys
sys.path.append("/opt/arm/arm")

import argparse
import os
import logging
import time
import datetime
import shutil
import pyudev
#import ripper.logger
#import ripper.utils
#import ripper.makemkv
#import ripper.handbrake
#import ripper.identify

from ripper import logger, utils, makemkv, handbrake, identify, getkeys
from config.config import cfg
# from classes import Disc
#from ripper.getkeys import grabkeys
from models.models import Job


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


def log_arm_params(job):
    """log all entry parameters"""

    # log arm parameters
    logging.info("**** Logging ARM variables ****")
    logging.info("devpath: " + str(job.devpath))
    logging.info("mountpoint: " + str(job.mountpoint))
    logging.info("videotitle: " + str(job.title))
    logging.info("videoyear: " + str(job.videoyear))
    logging.info("videotype: " + str(job.videotype))
    logging.info("hasnicetitle: " + str(job.hasnicetitle))
    logging.info("label: " + str(job.label))
    logging.info("disctype: " + str(job.disctype))
    logging.info("**** End of ARM variables ****")
    logging.info("**** Logging config parameters ****")
    logging.info("skip_transcode: " + str(cfg['SKIP_TRANSCODE']))
    logging.info("mainfeature: " + str(cfg['MAINFEATURE']))
    logging.info("minlength: " + cfg['MINLENGTH'])
    logging.info("maxlength: " + cfg['MAXLENGTH'])
    logging.info("videotype: " + cfg['VIDEOTYPE'])
    logging.info("ripmethod: " + cfg['RIPMETHOD'])
    logging.info("mkv_args: " + cfg['MKV_ARGS'])
    logging.info("delrawfile: " + str(cfg['DELRAWFILES']))
    logging.info("hb_preset_dvd: " + cfg['HB_PRESET_DVD'])
    logging.info("hb_preset_bd: " + cfg['HB_PRESET_BD'])
    logging.info("hb_args_dvd: " + cfg['HB_ARGS_DVD'])
    logging.info("hb_args_bd: " + cfg['HB_ARGS_BD'])
    logging.info("logfile: " + logfile)
    logging.info("armpath: " + cfg['ARMPATH'])
    logging.info("rawpath: " + cfg['RAWPATH'])
    logging.info("media_dir: " + cfg['MEDIA_DIR'])
    logging.info("extras_sub: " + cfg['EXTRAS_SUB'])
    logging.info("emby_refresh: " + str(cfg['EMBY_REFRESH']))
    logging.info("emby_server: " + cfg['EMBY_SERVER'])
    logging.info("emby_port: " + cfg['EMBY_PORT'])
    logging.info("notify_rip: " + str(cfg['NOTIFY_RIP']))
    logging.info("notify_transcode " + str(cfg['NOTIFY_TRANSCODE']))
    logging.info("**** End of config parameters ****")


def main(logfile, job):

    """main dvd processing function"""
    logging.info("Starting Disc identification")

    identify.identify(job, logfile)

    log_arm_params(job)

    if job.disctype in ["dvd", "bluray"]:
        utils.notify("ARM notification", "Found disc: " + str(job.title) + ". Video type is "
                     + str(job.videotype) + ". Main Feature is " + str(cfg['MAINFEATURE']) + ".")
    elif job.disctype == "music":
        utils.notify("ARM notification", "Found music CD: " + job.label + ". Ripping all tracks")
    elif job.disctype == "data":
        utils.notify("ARM notification", "Faound data disc.  Copying data.")
    else:
        utils.notify("ARM Notification", "Could not identify disc.  Exiting.")
        sys.exit()

    if cfg['HASHEDKEYS']:
        logging.info("Getting MakeMKV hashed keys for UHD rips")
        grabkeys()

    if job.disctype in ["dvd", "bluray"]:
        # get filesystem in order
        hboutpath = os.path.join(cfg['ARMPATH'], str(job.title))

        if (utils.make_dir(hboutpath)) is False:
            ts = round(time.time() * 100)
            hboutpath = os.path.join(cfg['ARMPATH'], str(job.title) + "_" + str(ts))
            if(utils.make_dir(hboutpath)) is False:
                logging.info("Failed to create base directory.  Exiting ARM.")
                sys.exit()

        logging.info("Processing files to: " + hboutpath)

        # Do the work!
        hbinpath = str(job.devpath)
        if job.disctype == "bluray" or not cfg['MAINFEATURE']:
            # send to makemkv for ripping
            # run MakeMKV and get path to ouput
            mkvoutpath = makemkv.makemkv(logfile, job)
            if mkvoutpath is None:
                logging.error("MakeMKV did not complete successfully.  Exiting ARM!")
                sys.exit()
            if cfg['NOTIFY_RIP']:
                utils.notify("ARM notification", str(job.title + " rip complete.  Starting transcode."))
            # point HB to the path MakeMKV ripped to
            hbinpath = mkvoutpath

            if cfg['SKIP_TRANSCODE'] and cfg['RIPMETHOD'] == "mkv":
                logging.info("SKIP_TRANSCODE is true.  Moving raw mkv files.")
                logging.info("NOTE: Identified main feature may not be actual main feature")
                files = os.listdir(mkvoutpath)
                final_directory = hboutpath
                if job.videotype == "movie":
                    logging.debug("Videotype: " + job.videotype)
                    # if videotype is movie, then move biggest title to media_dir
                    # move the rest of the files to the extras folder

                    # find largest filesize
                    logging.debug("Finding largest file")
                    largest_file_name = ""
                    for f in files:
                        # initialize largest_file_name
                        if largest_file_name == "":
                            largest_file_name = f
                        temp_path_f = os.path.join(hbinpath, f)
                        temp_path_largest = os.path.join(hbinpath, largest_file_name)
                        # os.path.join(cfg['MEDIA_DIR'] + videotitle)
                        # if cur file size > largest_file size
                        if(os.stat(temp_path_f).st_size > os.stat(temp_path_largest).st_size):
                            largest_file_name = f
                    # largest_file should be largest file
                    logging.debug("Largest file is: " + largest_file_name)
                    temp_path = os.path.join(hbinpath, largest_file_name)
                    if(os.stat(temp_path).st_size > 0):  # sanity check for filesize
                        for f in files:
                            # move main into media_dir
                            # move others into extras folder
                            if(f == largest_file_name):
                                # largest movie
                                utils.move_files(hbinpath, f, job.hasnicetitle, job.title + " (" + job.videoyear + ")", True)
                            else:
                                # other extras
                                if not str(cfg['EXTRAS_SUB']).lower() == "none":
                                    utils.move_files(hbinpath, f, job.hasnicetitle, job.title + " (" + job.videoyear + ")", False)
                                else:
                                    logging.info("Not moving extra: " + f)
                    # Change final path (used to set permissions)
                    final_directory = os.path.join(cfg['MEDIA_DIR'], job.title + " (" + job.videoyear + ")")
                    # Clean up
                    logging.debug("Attempting to remove extra folder in ARMPATH: " + hboutpath)
                    try:
                        shutil.rmtree(hboutpath)
                        logging.debug("Removed sucessfully: " + hboutpath)
                    except Exception:
                        logging.debug("Failed to remove: " + hboutpath)
                else:
                    # if videotype is not movie, then move everything
                    # into 'Unidentified' folder
                    logging.debug("Videotype: " + job.videotype)

                    for f in files:
                        mkvoutfile = os.path.join(mkvoutpath, f)
                        logging.debug("Moving file: " + mkvoutfile + " to: " + mkvoutpath + f)
                        shutil.move(mkvoutfile, hboutpath)
                # remove raw files, if specified in config
                if cfg['DELRAWFILES']:
                    logging.info("Removing raw files")
                    shutil.rmtree(mkvoutpath)
                # set file to default permissions '777'
                if cfg['SET_MEDIA_PERMISSIONS']:
                    perm_result = utils.set_permissions(final_directory)
                    logging.info("Permissions set successfully: " + str(perm_result))
                utils.notify("ARM notification", str(job.title) + " processing complete.")
                logging.info("ARM processing complete")
                # exit
                sys.exit()

        if job.disctype == "bluray" and cfg['RIPMETHOD'] == "mkv":
            handbrake.handbrake_mkv(hbinpath, hboutpath, logfile, job)
        elif job.disctype == "dvd" and not cfg['MAINFEATURE']:
            handbrake.handbrake_mkv(hbinpath, hboutpath, logfile, job)
        elif job.videotype == "movie" and cfg['MAINFEATURE']:
            handbrake.handbrake_mainfeature(hbinpath, hboutpath, logfile, job)
            job.eject()
        else:
            handbrake.handbrake_all(hbinpath, hboutpath, logfile, job)
            job.eject()

        # report errors if any
        if job.errors:
            errlist = ', '.join(job.errors)
            if cfg['NOTIFY_TRANSCODE']:
                utils.notify("ARM notification", str(job.title) + " processing completed with errors. Title(s) " + errlist + " failed to complete.")
            logging.info("Transcoding completed with errors.  Title(s) " + errlist + " failed to complete.")
        else:
            if cfg['NOTIFY_TRANSCODE']:
                utils.notify("ARM notification", str(job.title) + " processing complete.")
            logging.info("ARM processing complete")

        # Clean up bluray backup
        # if job.disctype == "bluray" and cfg["DELRAWFILES"]:
        if cfg['DELRAWFILES']:
            try:
                shutil.rmtree(mkvoutpath)
            except UnboundLocalError:
                logging.debug("No raw files found to delete.")
            except OSError:
                logging.debug("No raw files found to delete.")

    elif job.disctype == "music":
        if utils.rip_music(job, logfile):
            utils.notify("ARM notification", "Music CD: " + job.label + " processing complete.")
            utils.scan_emby()
        else:
            logging.info("Music rip failed.  See previous errors.  Exiting.")

    elif job.disctype == "data":
        # get filesystem in order
        datapath = os.path.join(cfg['ARMPATH'], str(job.label))
        if (utils.make_dir(datapath)) is False:
            ts = round(time.time() * 100)
            datapath = os.path.join(cfg['ARMPATH'], str(job.label) + "_" + str(ts))

            if(utils.make_dir(datapath)) is False:
                logging.info("Could not create data directory: " + datapath + ".  Exiting ARM.")
                sys.exit()

        if utils.rip_data(job, datapath, logfile):
            utils.notify("ARM notification", "Data disc: " + job.label + " copying complete.")
            job.eject()
        else:
            logging.info("Data rip failed.  See previous errors.  Exiting.")
            job.eject()

    else:
        logging.info("Couldn't identify the disc type. Exiting without any action.")


if __name__ == "__main__":
    args = entry()

    args.devpath = args.devpath[:3]
    devpath = "/dev/" + args.devpath
    print(devpath)

    job = Job(devpath)
    print("Job: " + job.label)

    # sys.exit()

    logfile = logger.setuplogging(job)
    print("Log: " + logfile)

    if utils.get_cdrom_status(devpath) != 4:
        logging.info("Drive appears to be empty or is not ready.  Exiting ARM.")
        sys.exit()

    logging.info("Starting ARM processing at " + str(datetime.datetime.now()))

    # Log version number
    with open(os.path.join(cfg['INSTALLPATH'], 'VERSION')) as version_file:
        version = version_file.read().strip()
    logging.info("ARM version: " + version)
    logging.info(("Python version: " + sys.version).replace('\n', ""))

    logger.cleanuplogs(cfg['LOGPATH'], cfg['LOGLIFE'])

    log_udev_params()

    try:
        main(logfile, job)
    except Exception:
        logging.exception("A fatal error has occured and ARM is exiting.  See traceback below for details.")
        utils.notify("ARM notification", "ARM encountered a fatal error processing " + str(job.title) + ". Check the logs for more details")
