#!/usr/bin/python3

import sys
import argparse
import os
# import re
import subprocess
import logging
import pprint
import time

def entry():
    """ Entry to program, parses arguments"""
    parser = argparse.ArgumentParser(description='Get type of dvd--movie or tv series')
    parser.add_argument('-d', '--devpath', help='Devpath', required=True)
    parser.add_argument('-m', '--minlength', help='Minimum Length', default=0, type=int)
    parser.add_argument('-x', '--maxlength', help='Maximum Length', default=0, type=int)
    parser.add_argument('-a', '--armpath', help='ArmPath', required=True)
    parser.add_argument('-r', '--rawpath', help='Rawpath', required=True)
    parser.add_argument('-e', '--label', help='Label', required=True)
    parser.add_argument('-b', '--handbrakecli', help='HandbrakeCLI', default="HandBrakeCLI")
    parser.add_argument('-p', '--hb_preset', help='Handbrake Preset', required=True)
    parser.add_argument('-g', '--hb_args', help='Handbrake Arguements', default='')
    parser.add_argument('-l', '--logfile', help='Logfile (path/logname)', required=True)

    return parser.parse_args()

def log_params():
    """log all entry parameters"""

    logging.info("Logging tv_dvd parameters")
    logging.info("**** Start tv_dvd.py paramaters *** ")
    logging.info("devpath: " + args.devpath)
    logging.info("minlength: " + str(args.minlength))
    logging.info("maxlength: " + str(args.maxlength))
    logging.info("armpath: " + args.armpath)
    logging.info("rawpath: " + args.rawpath)
    logging.info("handbrakecli: " + args.handbrakecli)
    logging.info("hb_preset: " + args.hb_preset)
    logging.info("logfile: " + args.logfile)
    logging.info("hb_args: " + args.hb_args)
    logging.info("*** End of tv_dvd.py parameters ***")

def main():
    """main tv processing function"""
    logging.info("Starting TV_DVD processing")

    try:
        d = subprocess.check_output(["lsdvd", '-Oy', args.devpath]).decode("utf-8")
    except subprocess.CalledProcessError as derror:
        print("Call to lsdvd failed with code: " + str(derror.returncode), derror.output)
        err = "Aborting.  Call to lsdvd failed with code: " + str(derror.returncode), derror.output
        sys.exit(err)

    data = d.replace("lsdvd = ", "", 1)
    info = eval(data, {})
    # print(info['track'])

    #get filesystem in order
    ts = round(time.time() * 100)
    basepath = os.path.join(args.armpath, args.label + "_" + str(ts))
    if not os.path.exists(basepath):
        try:
            os.makedirs(basepath)
        except:
            logging.error("Couldn't create the base file path: " + basepath + " Probably a permissions error")
            err = "Couldn't create the base file path: " + basepath + " Probably a permissions error"
            sys.exit(err)

    total = 0
    for index, item in enumerate(info['track']):
        if item['ix'] > total:
            total = item['ix']

    logging.info("Found " + str(total) + " tracks.")

    for index, item in enumerate(info['track']):

        if item['length'] < args.minlength:
            #too short
            logging.info("Track #" + str(item['ix']) + " of " + str(total) + ". Length (" + str(item['length']) + \
            ") is less than minimum length (" + str(args.minlength) + ").  Skipping")
        elif item['length'] > args.maxlength:
            #too long
            logging.info("Track #" + str(item['ix']) +" of " + str(total) + ". Length (" + str(item['length']) + \
            ") is greater than maximum length (" + str(args.maxlength) + ").  Skipping")
        else:
            #just right
            logging.info("Processing track #" + str(item['ix']) + " of " + str(total) + ". Length is " + str(item['length']) + " seconds.")


            filename = os.path.join(basepath, "title_" + str(item['ix']) + ".mkv")

            cmd = 'nice {0} -i "{1}" -o "{2}" --preset "{3}" -t {4} {5}>> {6}'.format(
                args.handbrakecli,
                args.devpath,
                filename,
                args.hb_preset,
                str(item['ix']),
                args.hb_args,
                args.logfile
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

args = entry()

#set up logging
logging.basicConfig(filename=args.logfile, format='[%(asctime)s] ARM: %(levelname)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S', \
level=logging.INFO)

log_params()
main()
