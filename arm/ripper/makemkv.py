import sys
import os
import logging
import subprocess
import time
import shlex

# from arm.config.config import cfg
from arm.ripper import utils  # noqa: E402
from arm.ui import db


def makemkv(logfile, job):
    """
    Rip Blurays with MakeMKV\n
    logfile = Location of logfile to redirect MakeMKV logs to\n
    job = job object\n

    Returns path to ripped files.
    """

    logging.info("Starting MakeMKV rip. Method is " + job.config.RIPMETHOD)

    # get MakeMKV disc number
    logging.debug("Getting MakeMKV disc number")
    cmd = 'makemkvcon -r info disc:9999  |grep {0} |grep -oP \'(?<=:).*?(?=,)\''.format(
                job.devpath
    )

    try:
        mdisc = subprocess.check_output(
            cmd,
            shell=True
        ).decode("utf-8")
        logging.info("MakeMKV disc number: " + mdisc.strip())
        # print("mdisc is: " + mdisc)
    except subprocess.CalledProcessError as mdisc_error:
        err = "Call to makemkv failed with code: " + str(mdisc_error.returncode) + "(" + str(mdisc_error.output) + ")"
        logging.error(err)
        raise RuntimeError(err)

    # get filesystem in order
    rawpath = os.path.join(str(job.config.RAWPATH), str(job.title))
    logging.info("Destination is " + str(rawpath))

    if not os.path.exists(rawpath):
        try:
            os.makedirs(rawpath)
        except OSError:
            # logging.error("Couldn't create the base file path: " + rawpath + " Probably a permissions error")
            err = "Couldn't create the base file path: " + str(rawpath) + " Probably a permissions error"
    else:
        logging.info(rawpath + " exists.  Adding timestamp.")
        ts = round(time.time() * 100)
        rawpath = os.path.join(str(job.config.RAWPATH), str(job.title) + "_" + str(ts))
        logging.info("rawpath is " + str(rawpath))
        try:
            os.makedirs(rawpath)
        except OSError:
            # logging.error("Couldn't create the base file path: " + rawpath + " Probably a permissions error")
            err = "Couldn't create the base file path: " + str(rawpath) + " Probably a permissions error"
            sys.exit(err)

    # rip bluray
    if job.config.RIPMETHOD == "backup" and job.disctype == "bluray":
        # backup method
        cmd = 'makemkvcon backup --decrypt {0} -r disc:{1} {2}>> {3}'.format(
            job.config.MKV_ARGS,
            mdisc.strip(),
            shlex.quote(rawpath),
            logfile
        )
        logging.info("Backup up disc")
        logging.debug("Backing up with the following command: " + cmd)

        try:
            mkv = subprocess.run(
                cmd,
                shell=True
            )
            # ).decode("utf-8")
            # print("mkv is: " + mkv)
            logging.debug("The exit code for MakeMKV is: " + str(mkv.returncode))
            if mkv.returncode == 253:
                # Makemkv is out of date
                err = "MakeMKV version is too old.  Upgrade and try again.  MakeMKV returncode is '253'."
                logging.error(err)
                raise RuntimeError(err)
        except subprocess.CalledProcessError as mdisc_error:
            err = "Call to MakeMKV failed with code: " + str(mdisc_error.returncode) + "(" + str(mdisc_error.output) + ")"
            logging.error(err)
            # print("Error: " + mkv)
            return None

    elif job.config.RIPMETHOD == "mkv" or job.disctype == "dvd":
        # mkv method
        get_track_info(mdisc, job)

        # if no maximum length, process the whole disc in one command
        if int(job.config.MAXLENGTH) > 99998:
            cmd = 'makemkvcon mkv {0} -r dev:{1} {2} {3} --minlength={4}>> {5}'.format(
                job.config.MKV_ARGS,
                job.devpath,
                "all",
                shlex.quote(rawpath),
                job.config.MINLENGTH,
                logfile
            )
            logging.debug("Ripping with the following command: " + cmd)

            try:
                mkv = subprocess.run(
                    cmd,
                    shell=True
                )
                # ).decode("utf-8")
                # print("mkv is: " + mkv)
                logging.debug("The exit code for MakeMKV is: " + str(mkv.returncode))
                if mkv.returncode == 253:
                    # Makemkv is out of date
                    err = "MakeMKV version is too old.  Upgrade and try again.  MakeMKV returncode is '253'."
                    logging.error(err)
                    raise RuntimeError(err)
            except subprocess.CalledProcessError as mdisc_error:
                err = "Call to MakeMKV failed with code: " + str(mdisc_error.returncode) + "(" + str(mdisc_error.output) + ")"
                logging.error(err)
                # print("Error: " + mkv)
                return None
        else:
            # process one track at a time based on track length
            for track in job.tracks:
                if track.length < int(job.config.MINLENGTH):
                    # too short
                    logging.info("Track #" + str(track.track_number) + " of " + str(job.no_of_titles) + ". Length (" + str(track.length) +
                                 ") is less than minimum length (" + job.config.MINLENGTH + ").  Skipping")
                elif track.length > int(job.config.MAXLENGTH):
                    # too long
                    logging.info("Track #" + str(track.track_number) + " of " + str(job.no_of_titles) + ". Length (" + str(track.length) +
                                 ") is greater than maximum length (" + job.config.MAXLENGTH + ").  Skipping")
                else:
                    # just right
                    logging.info("Processing track #" + str(track.track_number) + " of " + str(job.no_of_titles - 1) + ". Length is " +
                                 str(track.length) + " seconds.")

                    # filename = "title_" + str.zfill(str(track.track_number), 2) + "." + cfg['DEST_EXT']
                    # filename = track.filename
                    filepathname = os.path.join(rawpath, track.filename)

                    logging.info("Ripping title " + str(track.track_number) + " to " + shlex.quote(filepathname))

                    # track.filename = track.orig_filename = filename
                    # db.session.commit()

                    cmd = 'makemkvcon mkv {0} -r dev:{1} {2} {3} --minlength={4}>> {5}'.format(
                        job.config.MKV_ARGS,
                        job.devpath,
                        str(track.track_number),
                        shlex.quote(rawpath),
                        job.config.MINLENGTH,
                        logfile
                    )
                    logging.debug("Ripping with the following command: " + cmd)

                    try:
                        mkv = subprocess.run(
                            cmd,
                            shell=True
                        )
                        # ).decode("utf-8")
                        # print("mkv is: " + mkv)
                        logging.debug("The exit code for MakeMKV is: " + str(mkv.returncode))
                        if mkv.returncode == 253:
                            # Makemkv is out of date
                            err = "MakeMKV version is too old.  Upgrade and try again.  MakeMKV returncode is '253'."
                            logging.error(err)
                            raise RuntimeError(err)
                    except subprocess.CalledProcessError as mdisc_error:
                        err = "Call to MakeMKV failed with code: " + str(mdisc_error.returncode) + "(" + str(mdisc_error.output) + ")"
                        logging.error(err)
                        # print("Error: " + mkv)
                        return None

    else:
        logging.info("I'm confused what to do....  Passing on MakeMKV")

    job.eject()

    logging.info("Exiting MakeMKV processing with return value of: " + rawpath)
    return(rawpath)


def get_track_info(mdisc, job):
    """Use MakeMKV to get track info and updatte Track class\n

    mdisc = MakeMKV disc number\n
    job = Job instance\n
    """

    logging.info("Using MakeMKV to get information on all the tracks on the disc.  This will take a few minutes...")

    cmd = 'makemkvcon -r --cache=1 info disc:{0}'.format(
        mdisc
    )

    logging.debug("Sending command: %s", (cmd))

    try:
        mkv = subprocess.check_output(
            cmd,
            stderr=subprocess.STDOUT,
            shell=True
        ).decode("utf-8").splitlines()
    except subprocess.CalledProcessError as mdisc_error:
        err = "Call to MakeMKV failed with code: " + str(mdisc_error.returncode) + "(" + str(mdisc_error.output) + ")"
        logging.error(err)
        return None

    track = 0
    fps = float(0)
    aspect = ""
    seconds = 0
    filename = ""

    for line in mkv:
        if line.split(":")[0] in ("MSG", "TCOUNT", "CINFO", "TINFO", "SINFO"):
            # print(line.rstrip())
            line_split = line.split(":", 1)
            msg_type = line_split[0]
            msg = line_split[1].split(",")
            line_track = int(msg[0])

            if msg_type == "MSG":
                if msg[0] == "5055":
                    job.errors = "MakeMKV evaluation period has expired.  DVD processing will continus.  Bluray processing will exit."
                    if job.disctype == "bluray":
                        err = "MakeMKV evaluation period has expired.  Disc is a Bluray so ARM is exiting"
                        logging.error(err)
                        raise ValueError(err, "makemkv")
                    else:
                        logging.error("MakeMKV evaluation perios has ecpires.  Disc is dvd so ARM will continue")
                    db.session.commit()

            if msg_type == "TCOUNT":
                titles = int(line_split[1].strip())
                logging.info("Found " + str(titles) + " titles")
                job.no_of_titles = titles
                db.session.commit()

            if msg_type == "TINFO":
                if track != line_track:
                    if line_track == int(0):
                        pass
                    else:
                        utils.put_track(job, track, seconds, aspect, fps, False, "makemkv", filename)
                    track = line_track

                if msg[1] == "27":
                    filename = msg[3].replace('"', '').strip()

            if msg_type == "TINFO" and msg[1] == "9":
                len_hms = msg[3].replace('"', '').strip()
                h, m, s = len_hms.split(':')
                seconds = int(h) * 3600 + int(m) * 60 + int(s)

            if msg_type == "SINFO" and msg[1] == "0":
                if msg[2] == "20":
                    aspect = msg[4].replace('"', '').strip()
                elif msg[2] == "21":
                    fps = msg[4].split()[0]
                    fps = fps.replace('"', '').strip()
                    fps = float(fps)

    utils.put_track(job, track, seconds, aspect, fps, False, "makemkv", filename)
