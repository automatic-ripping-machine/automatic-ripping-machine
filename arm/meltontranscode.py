import subprocess
import logging
import os
import shlex

from config import cfg


def find_crop(path_to_media_file):
    """Detects the crop of a file using don meltons detect-crop cli utility"""

    cmd = "detect-crop --constrain --values-only {0}".format(path_to_media_file)
    print("Sending command: {0}".format(cmd))
    try:
        fc = subprocess.check_output(
            cmd,
            shell=True
        ).decode("utf-8")
    except subprocess.CalledProcessError:
        fc = "0:0:0:0"

    return fc.strip()


def melton_mkv(srcpath, basepath, logfile, disc):
    """process all mkv files in a directory.\n
    srcpath = Path to source for HB (dvd or files)\n
    basepath = Path where HB will save trancoded files\n
    logfile = Logfile for HB to redirect output to\n
    disc = Disc object\n

    Returns nothing
    """

    if disc.disctype == "dvd":
        mt_args = cfg['MT_ARGS_DVD']
    elif disc.disctype == "bluray":
        mt_args = cfg['MT_ARGS_BD']
    else:
        logging.error('Something went wrong here')
        exit()

    for f in os.listdir(srcpath):
        srcpathname = os.path.join(srcpath, f)
        destfile = os.path.splitext(f)[0]
        filename = os.path.join(basepath, destfile + "." + cfg['DEST_EXT'])
        filepathname = os.path.join(basepath, filename)

        logging.info("Transcoding file " + shlex.quote(f) + " to " + shlex.quote(filepathname))

        crop = find_crop(srcpathname)

        cmd = 'nice {0} {1} --crop {2} -o {3} {4}>> {5} 2>&1'.format(
            cfg['MELTON_CLI'],
            mt_args,
            crop,
            filepathname,
            srcpathname,
            logfile
        )

        logging.debug("Sending command: %s", (cmd))

        try:
            mt = subprocess.check_output(
                cmd,
                shell=True
            ).decode("utf-8")
            logging.debug("Handbrake exit code: " + mt)
        except subprocess.CalledProcessError as mt_error:
            err = "MeltonTranscode encoding of file " + shlex.quote(f) + " failed with code: " + str(mt_error.returncode) + "(" + str(mt_error.output) + ")"
            logging.error(err)
            disc.errors.append(f)

    logging.info("Melton Transcode processing complete")
    logging.debug(str(disc))


def main():
    pass


if __name__ == "__main__":
    main()