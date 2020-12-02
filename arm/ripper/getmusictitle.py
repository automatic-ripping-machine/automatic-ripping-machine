#!/usr/bin/python3
from discid import read
import logging
import re
import musicbrainzngs as mb
from subprocess import run, PIPE
from arm.config.config import cfg
from arm.ui import app, db  # noqa E402


# from classes import Disc


def main(disc):
    """
    Depending on the configuration musicbrainz or freedb is used
    to identify the music disc. The label of the disc is returned
    or "".
    """
    discid = get_discid(disc)
    if cfg['GET_AUDIO_TITLE'] == 'musicbrainz':
        return musicbrainz(discid, disc)
    elif cfg['GET_AUDIO_TITLE'] == 'freecddb':
        return cddb(discid)
    elif cfg['GET_AUDIO_TITLE'] == 'none':
        return ""
    else:
        return ""


def get_discid(disc):
    """
    Calculates the identifier of the disc

    return:
    identification object from discid package
    """
    return read(disc.devpath)


def musicbrainz(discid, job):
    """
    Ask musicbrainz.org for the release of the disc

    arguments:
    discid - identification object from discid package

    return:
    the label of the disc as a string or "" if nothing was found
    """
    mb.set_useragent("arm", "v1.0")

    ## TODO: Split this into smaller groups of tries so we dont lose everything if a single thing fails
    try:
        infos = mb.get_releases_by_discid(discid, includes=['artist-credits'])
        logging.debug("Infos: %s", infos)
        ## Clean up the date and the tiotle
        new_year = str(infos['disc']['release-list'][0]['date'])
        new_year = re.sub("-[0-9]{2}-[0-9]{2}$", "", new_year)
        title = str(infos['disc']['release-list'][0]['title'])
        ##Set out release id as the CRC_ID
        job.crc_id = infos['disc']['release-list'][0]['id']
        logging.debug("musicbrain works -  New title is " + title + ".  New Year is: " + new_year)
    except mb.WebServiceError as exc:
        logging.error("Cant reach MB ? - ERROR: " + str(exc))
        db.session.commit()
        return ""
    db.session.commit()
    try:
        ## We never make it to here if the mb fails
        artist = infos['disc']['release-list'][0]['artist-credit'][0]['artist']['name']
        logging.debug("artist=====" + str(artist))
        logging.debug("we have artwork======" + infos['disc']['release-list'][0]['cover-art-archive']['artwork'])

        ## Get our front cover if it exists
        if infos['disc']['release-list'][0]['cover-art-archive']['artwork'] != "false":
            artlist = mb.get_image_list(job.crc_id)
            for image in artlist["images"]:
                if "Front" in image["types"] and image["approved"]:
                    job.poster_url_auto = str(image["thumbnails"]["large"])
                    job.poster_url = str(image["thumbnails"]["large"])
                    break
        ## Set up the database properly for music cd's
        job.logfile = cleanforlog(artist) + "_" + cleanforlog(infos['disc']['release-list'][0]['title']) + ".log"
        job.year = job.year_auto = str(new_year)
        job.title = job.title_auto = artist + " " + title
        job.hasnicetitle = True
        job.no_of_titles = infos['disc']['offset-count']
        job.video_type = "Music"
        db.session.commit()
        return artist + " " + str(infos['disc']['release-list'][0]['title'])
    except Exception as exc:
        logging.error("Try 2 -  ERROR: " + str(exc))
        db.session.commit()
        return artist + " " + str(infos['disc']['release-list'][0]['title'])


def cddb(discid):
    """
    Ask freedb.org for the label of the disc and uses the command line tool
    cddb-tool from abcde

    arguments:
    discid - identification object from discid package

    return:
    the label of the disc as a string or "" if nothing was found
    """
    cddburl = "http://freedb.freedb.org/~cddb/cddb.cgi"
    command = ['cddb-tool', 'query', cddburl, '6', 'arm', 'armhost', discid.freedb_id, str(len(discid.tracks))]
    command += [str(track.offset) for track in discid.tracks]
    command += [str(discid.seconds)]
    logging.debug("command: %s", " ".join(command))
    ret = run(command, stdout=PIPE, universal_newlines=True)
    if ret.returncode == 0:
        infos = [line for line in ret.stdout.split("\n")]
        logging.debug("Infos: %s", infos)
        firstline = infos[0].split(" ")
        status = int(firstline[0])
        logging.debug("status: %d, firstline: %s", status, firstline)
        if status == 200:  # excat match
            title = " ".join(firstline[3:])
        elif status == 210 or status == 211:  # multiple
            infos = infos[-3]  # last entry
            title = " ".join(infos.split(" ")[2:])
        else:  # nothing found
            title = ""
        return title
    else:
        return ""


def cleanforlog(s):
    a = str(s).replace(" ", "_")
    return a


def gettitle(discid, job):
    mb.set_useragent("arm", "v1.0")
    try:
        infos = mb.get_releases_by_discid(discid, includes=['artist-credits'])
        title = str(infos['disc']['release-list'][0]['title'])
        ##Start setting our db stuff
        job.crc_id = infos['disc']['release-list'][0]['id']
        artist = infos['disc']['release-list'][0]['artist-credit'][0]['artist']['name']
        job.logfile = cleanforlog(artist) + "_" + cleanforlog(infos['disc']['release-list'][0]['title']) + ".log"
        job.title = job.title_auto = artist + " " + title
        db.session.commit()
        return job.title
    except mb.WebServiceError as exc:
        logging.error("######### ERROR: " + str(exc))
        if str(infos['disc']['release-list'][0]['title']) != "":
            return infos['disc']['release-list'][0]['title']
        return ""


if __name__ == "__main__":
    # test code
    logging.basicConfig(level=logging.DEBUG)
    disc = Disc("/dev/cdrom")
    myid = get_discid(disc)
    logging.info("DiscID: %s (%s)", str(myid), myid.freedb_id)
    logging.info("URL: %s", myid.submission_url)
    logging.info("Tracks: %s", myid.tracks)
    logging.info("Musicbrain: %s", musicbrainz(myid))

    logging.info("freedb: %s", cddb(myid))
