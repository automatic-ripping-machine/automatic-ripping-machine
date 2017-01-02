#!/usr/bin/python3

import sys
import argparse
import os
# import re
import subprocess
import logging
import pprint

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

    # logging.info("Logging tv_dvd parameters")
    # logging.info("Input parameters are: ")
    # logging.info(args.devpath)
    # logging.info(args.minlength)
    # logging.info(args.maxlength)
    # logging.info(args.armpath)
    # logging.info(args.rawpath)
    # logging.info(args.handbrakecli)
    # logging.info(args.hb_preset)
    # logging.info(args.logfile)

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

    for index, item in enumerate(info['track']):
        # print(index, item['ix'], item['length'])
        # print("Track #" + str(item['ix']) + " is " + str(item['length']) + " long.")

        if item['length'] < args.minlength:
            #too short
            logging.info("Track #" + str(item['ix']) + " length (" + str(item['length']) + \
            ") is less than minimum length (" + str(args.minlength) + ").  Skipping")
        elif item['length'] > args.maxlength:
            #too long
            logging.info("Track #" + str(item['ix']) + " length (" + str(item['length']) + \
            ") is greater than maximum length (" + str(args.maxlength) + ").  Skipping")
        else:
            #just right
            #get filesystem in order
            logging.info("Processing track #" + str(item['ix']) + ". Length is " + str(item['length']) + " seconds.")
            basepath = os.path.join(args.rawpath, args.label)
            if not os.path.exists(basepath):
                try:
                    os.makedirs(basepath)
                except:
                    logging.error("Couldn't create the base file path: " + basepath + " Probably a permissions error")
                    err = "Couldn't create the base file path: " + basepath + " Probably a permissions error"
                    sys.exit(err)

            filename = os.path.join(basepath, "title_" + str(item['ix']) + ".mkv")
            # logging.info(args.handbrakecli + " -i " + args.devpath + " -o " + filename + " -t" +  \
            # str(item['ix']) + " --preset \"" + args.hb_preset + "\" --subtitle scan -F 2")

            #call handbrake
            # try:
            #     hb = subprocess.check_output([args.handbrakecli, "-i " + args.devpath, \
            #     "-o \"" + filename + "\"", "-t " + str(item['ix']), \
            #     "--preset \"" + args.hb_preset + "\"", "--subtitle scan", "-F 2"]).decode("utf-8")
            #     cmd = "Handbrake command sent is: " + hb.args
            #     logging.info(cmd)
            # except subprocess.CalledProcessError as hb_error:
            #     err = "Call to hadnbrake failed with code: " + str(hb_error.returncode) + "(" + str(hb_error.output) + ")"
            #     logging.error(err)
            #     sys.exit(err)
            
            cmd = 'nice {0} -i "{1}" -o "{2}" --preset "{3}" -t {4} {5}>> {6}'.format(
                args.handbrakecli,
                args.devpath,
                filename,
                args.hb_preset,
                str(item['ix']),
                args.hb_args,
                args.logfile
                )

            logging.info("Sending command: %s", (cmd))

            # try:
            #     hb = subprocess.check_output(
            #         cmd,
            #         # stdout=subprocess.PIPE,
            #         # stderr=subprocess.STDOUT,
            #         shell=True
            #     ).decode("utf-8")
            # except subprocess.CalledProcessError as hb_error:
            #     err = "Call to hadnbrake failed with code: " + str(hb_error.returncode) + "(" + str(hb_error.output) + ")"
            #     logging.error(err)
            #     sys.exit(err)

            # if hb.returncode is not 0:
            #     err = "Call to hadnbrake failed with code: " + str(hb.returncode)
            #     logging.error(err)
            #     sys.exit(err)



args = entry()

#set up logging
logging.basicConfig(filename=args.logfile, format='[%(asctime)s] ARM: %(levelname)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S', \
level=logging.INFO)

main()
