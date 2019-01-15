#!/usr/bin/python3

import sys
import os
import logging
import subprocess
import re
import shlex

from arm.config.config import cfg
from arm.models.models import Track  # noqa: E402
from arm.ui import app, db # noqa E402


def handbrake_mainfeature(srcpath, basepath, logfile, job):
    """process dvd with mainfeature enabled.\n
    srcpath = Path to source for HB (dvd or files)\n
    basepath = Path where HB will save trancoded files\n
    logfile = Logfile for HB to redirect output to\n
    job = Job object\n

    Returns nothing
    """
    logging.info("Starting DVD Movie Mainfeature processing")
    logging.debug("Handbrake starting: " + str(job))
    # logging.debug("Job ID: " + job.job_id)

    filename = os.path.join(basepath, job.title + ".mkv")
    filepathname = os.path.join(basepath, filename)
    # Dict of files created in filename:ismaintitle format
    # titles_in_out = {}

    get_track_info(srcpath, job)

    track = job.tracks.filter_by(main_feature=True).first()

    logging.info("Ripping title Mainfeature to " + shlex.quote(filepathname))

    # t = Track(track_number="0", main_feature=True, basename=job.title, orig_filename=job.title + ".mkv", filename=job.title + ".mkv", job_id=job.job_id)
    # db.session.add(t)
    # db.session.commit()

    if job.disctype == "dvd":
        hb_args = cfg['HB_ARGS_DVD']
        hb_preset = cfg['HB_PRESET_DVD']
    elif job.disctype == "bluray":
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
    logging.debug(str(job))

    track.ripped = True
    db.session.commit()

    return

    # titles_in_out[filename] = True

    # utils.move_files(basepath, filename, job, True)
    # utils.scan_emby()

    # try:
    #     os.rmdir(basepath)
    # except OSError:
    #     pass


def handbrake_all(srcpath, basepath, logfile, job):
    """Process all titles on the dvd\n
    srcpath = Path to source for HB (dvd or files)\n
    basepath = Path where HB will save trancoded files\n
    logfile = Logfile for HB to redirect output to\n
    job = Disc object\n

    Returns nothing
    """
    logging.info("Starting BluRay/DVD transcoding - All titles")

    # titles_in_out = {}

    # # get number of titles
    # logging.info("Getting total number of titles on disc.  This will take a minute or two...")
    # cmd = '{0} -i {1} -t 0 --scan'.format(
    #     cfg['HANDBRAKE_CLI'],
    #     shlex.quote(srcpath)
    #     )

    # logging.debug("Sending command: %s", (cmd))

    # try:
    #     hb = subprocess.run(
    #         cmd,
    #         stderr=subprocess.PIPE,
    #         shell=True
    #     )
    # except subprocess.CalledProcessError as hb_error:
    #     err = "Call to handbrake failed with code: " + str(hb_error.returncode) + "(" + str(hb_error.output) + ")"
    #     logging.error(err)
    #     sys.exit(err)

    get_track_info(srcpath, job)

    # titles = db.session.query(Track).filter_by(job_id=job.job_id).count()
    # titles = job.no_of_titles
    logging.debug("Total number of tracks is " + str(job.no_of_titles))

    # mt_track = 0
    # prevline = ""
    # for line in hb.stderr.decode(errors='ignore').splitlines(True):

    if job.disctype == "dvd":
        hb_args = cfg['HB_ARGS_DVD']
        hb_preset = cfg['HB_PRESET_DVD']
    elif job.disctype == "bluray":
        hb_args = cfg['HB_ARGS_BD']
        hb_preset = cfg['HB_PRESET_BD']

    for track in job.tracks:
        # get number of titles on disc
        # pattern = re.compile(r'\bscan\:.*\btitle\(s\)')

        #     if job.disctype == "bluray":
        #         result = re.search('scan: BD has (.*) title\(s\)', line)
        #     else:
        #         result = re.search('scan: DVD has (.*) title\(s\)', line)

        #     if result:
        #         titles = result.group(1)
        #         titles = titles.strip()
        #         logging.debug("Line found is: " + line)
        #         logging.info("Found " + titles + " titles")

        #     # get main feature title number
        #     if(re.search("Main Feature", line)) is not None:
        #         t = prevline.split()
        #         mt_track = re.sub('[:]', '', (t[2]))
        #         logging.debug("Lines found are: 1) " + line.rstrip() + " | 2)" + prevline)
        #         logging.info("Main Feature is title #" + mt_track)
        #     prevline = line

        # if titles == 0:
        #     raise ValueError("Couldn't get total number of tracks", "handbrake_all")

        # mt_track = str(mt_track).strip()

        # for title in range(1, int(titles) + 1):

            # get length
            # tlength = get_title_length(title, srcpath)

        if track.length < int(cfg['MINLENGTH']):
            # too short
            logging.info("Track #" + str(track.track_number) + " of " + str(job.no_of_titles) + ". Length (" + str(track.length) +
                         ") is less than minimum length (" + cfg['MINLENGTH'] + ").  Skipping")
        elif track.length > int(cfg['MAXLENGTH']):
            # too long
            logging.info("Track #" + str(track.track_number) + " of " + str(job.no_of_titles) + ". Length (" + str(track.length) +
                         ") is greater than maximum length (" + cfg['MAXLENGTH'] + ").  Skipping")
        else:
            # just right
            logging.info("Processing track #" + str(track.track_number) + " of " + str(job.no_of_titles) + ". Length is " + str(track.length) + " seconds.")

            filename = "title_" + str.zfill(str(track.track_number), 2) + "." + cfg['DEST_EXT']
            filepathname = os.path.join(basepath, filename)

            logging.info("Transcoding title " + str(track.track_number) + " to " + shlex.quote(filepathname))

            cmd = 'nice {0} -i {1} -o {2} --preset "{3}" -t {4} {5}>> {6} 2>&1'.format(
                cfg['HANDBRAKE_CLI'],
                shlex.quote(srcpath),
                shlex.quote(filepathname),
                hb_preset,
                str(track.track_number),
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
                err = "Handbrake encoding of title " + str(track.track_number) + " failed with code: " + str(hb_error.returncode) + "(" + str(hb_error.output) + ")"  # noqa E501
                logging.error(err)
                job.errors.append(str(track.track_number))
                # return
                # sys.exit(err)

            track.ripped = True
            db.session.commit()

            # # move file
            # # if job.video_type == "movie":
            # logging.debug("mt_track: " + mt_track + " List track: " + str(track.track_number))
            # if mt_track == str(track.track_number) and job.video_type == "movie":
            #     titles_in_out[filename] = True
            #     # utils.move_files(basepath, filename, job, True)
            # else:
            #     titles_in_out[filename] = False
            #     # utils.move_files(basepath, filename, job, False)

    logging.info("Handbrake processing complete")
    logging.debug(str(job))

    return

    # return titles_in_out
    # if job.video_type == "movie" and job.hasnicetitle:
    #     utils.scan_emby()
    #     try:
    #         os.rmdir(basepath)
    #     except OSError:
    #         pass


def handbrake_mkv(srcpath, basepath, logfile, job):
    """process all mkv files in a directory.\n
    srcpath = Path to source for HB (dvd or files)\n
    basepath = Path where HB will save trancoded files\n
    logfile = Logfile for HB to redirect output to\n
    job = Disc object\n

    Returns nothing
    """

    if job.disctype == "dvd":
        hb_args = cfg['HB_ARGS_DVD']
        hb_preset = cfg['HB_PRESET_DVD']
    elif job.disctype == "bluray":
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
            # job.errors.append(f)

    logging.info("Handbrake processing complete")
    logging.debug(str(job))

    return


# def get_title_length(title, srcpath):
#     """Use HandBrake to get the title length\n
#     title = title to scan\n
#     srcpath = location of the dvd or decrypted bluray\n

#     returns the length of the title or -1 if the length could not be determinied
#     """
#     logging.debug("Getting length from " + srcpath + " on title: " + str(title))

#     cmd = '{0} -i {1} -t {2} --scan'.format(
#         cfg['HANDBRAKE_CLI'],
#         shlex.quote(srcpath),
#         title
#         )

#     logging.debug("Sending command: %s", (cmd))

#     try:
#         hb = subprocess.check_output(
#             cmd,
#             stderr=subprocess.STDOUT,
#             shell=True
#         ).decode("utf-8").splitlines()
#     except subprocess.CalledProcessError as hb_error:
#         # err = "Call to handbrake failed with code: " + str(hb_error.returncode) + "(" + str(hb_error.output) + ")"
#         logging.debug("Couldn't find a valid track.  Try running the command manually to see more specific errors.")
#         return(-1)
#         # sys.exit(err)

#     pattern = re.compile(r'.*duration\:.*')
#     for line in hb:
#         if(re.search(pattern, line)) is not None:
#             t = line.split()
#             h, m, s = t[2].split(':')
#             seconds = int(h) * 3600 + int(m) * 60 + int(s)
#             return(seconds)


def get_track_info(srcpath, job):
    """Use HandBrake to get track info and updatte Track class\n

    srcpath = Path to disc\n
    job = Job instance\n
    """

    logging.info("Getting information on all the tracks on the disc.  This will take a few minutes...")

    cmd = '{0} -i {1} -t 0 --scan'.format(
        cfg['HANDBRAKE_CLI'],
        shlex.quote(srcpath)
        )

    # logging.debug("Sending command: %s", (cmd))

    try:
        hb = subprocess.check_output(
            cmd,
            stderr=subprocess.STDOUT,
            shell=True
        ).decode("utf-8").splitlines()
    except subprocess.CalledProcessError as hb_error:
        # err = "Call to handbrake failed with code: " + str(hb_error.returncode) + "(" + str(hb_error.output) + ")"
        logging.error("Couldn't find a valid track.  Try running the command manually to see more specific errors.")
        return(-1)
        # sys.exit(err)

    def put_track(job, t_no, seconds, b, a, f, mainfeature):

        logging.debug("Track #" + str(t_no) + " Length: " + str(seconds) + " seconds Blocks: " + str(b) + " fps: "
                      + str(f) + " aspect: " + str(a) + " Mainfeature: " + str(mainfeature))

        t = Track(
            job_id=job.job_id,
            track_number=t_no,
            length=seconds,
            aspect_ratio=a,
            blocks=b,
            fps=f,
            main_feature=mainfeature,
            basename=job.title,
            filename=job.title + ".mkv",
            orig_filename=job.title + ".mkv"
            )
        db.session.add(t)
        db.session.commit()

    t_pattern = re.compile(r'.*\+ title *')
    pattern = re.compile(r'.*duration\:.*')
    b_pattern = re.compile(r'.*blocks\).*')
    seconds = 0
    t_no = 0
    b = 0
    f = 0
    a = 0
    result = ""
    mainfeature = False
    for line in hb:

        # get number of titles
        if result == "":
            if job.disctype == "bluray":
                result = re.search('scan: BD has (.*) title\(s\)', line)
            else:
                result = re.search('scan: DVD has (.*) title\(s\)', line)

            if result:
                titles = result.group(1)
                titles = titles.strip()
                # logging.debug("Line found is: " + line)
                logging.info("Found " + titles + " titles")
                job.no_of_titles = titles
                db.session.commit()

        if(re.search(t_pattern, line)) is not None:
            if t_no == 0:
                pass
            else:
                put_track(job, t_no, seconds, b, a, f, mainfeature)

            mainfeature = False
            t_no = line.rsplit(' ', 1)[-1]
            t_no = t_no.replace(":", "")
            # print("Found Track " + t_no)

        if(re.search(pattern, line)) is not None:
            t = line.split()
            h, m, s = t[2].split(':')
            seconds = int(h) * 3600 + int(m) * 60 + int(s)

        if(re.search("Main Feature", line)) is not None:
            mainfeature = True

        if(re.search(b_pattern, line)) is not None:
            b = line.rsplit(' ', 2)[-2]
            b = b.replace("(", "")

        if(re.search(" fps", line)) is not None:
            f = line.rsplit(' ', 2)[-2]
            a = line.rsplit(' ', 3)[-3]
            a = str(a).replace(",", "")

    put_track(job, t_no, seconds, b, a, f, mainfeature)
