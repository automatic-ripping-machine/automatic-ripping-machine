#!/usr/bin/env python3
import logging
import re
import time
import musicbrainzngs as mb
from discid import read, Disc

from arm.config.config import cfg
from arm.ui import app, db  # noqa E402
import werkzeug
werkzeug.cached_property = werkzeug.utils.cached_property
from robobrowser import RoboBrowser  # noqa E402


def main(disc):
    """
    Depending on the configuration musicbrainz is used
    to identify the music disc. The label of the disc is returned
    or "".
    """
    discid = get_disc_id(disc)
    if cfg['GET_AUDIO_TITLE'] == 'musicbrainz':
        return music_brainz(discid, disc)
    else:
        return ""


def get_disc_id(disc):
    """
    Calculates the identifier of the disc

    return:
    identification object from discid package
    """
    return read(disc.devpath)


def music_brainz(discid, job):
    """
    Ask musicbrainz.org for the release of the disc

    arguments:
    discid - identification object from discid package
    job - the job class/obj

    return:
    the label of the disc as a string or "" if nothing was found
    """
    mb.set_useragent("arm", "v2.4")
    # TODO: Split this into smaller groups of tries so we dont lose everything if a single thing fails
    try:
        infos = mb.get_releases_by_discid(discid, includes=['artist-credits'])
        logging.debug("Infos: %s", infos)
        logging.debug("discid = " + str(discid))
        release = infos['disc']['release-list'][0]
        # Clean up the date and the title
        if 'date' in release:
            new_year = str(release['date'])
            new_year = re.sub("-[0-9]{2}-[0-9]{2}$", "", new_year)
        else:
            # sometimes there is no date in a release
            new_year = ""
        title = str(release.get('title', 'no title'))
        # Set out release id as the CRC_ID
        # job.crc_id = release['id']
        # job.hasnicetitle = True
        args = {
            'job_id': str(job.job_id),
            'crc_id': release['id'],
            'hasnicetitle': True,
            'year': str(new_year),
            'year_auto': str(new_year),
            'title': title,
            'title_auto': title
        }
        database_updater(args, job)
        # db.session.commit()
        # time.sleep(1)
        logging.debug("musicbrain works -  New title is " + title + ".  New Year is: " + new_year)
    except mb.WebServiceError as exc:
        logging.error("Cant reach MB or cd not found ? - ERROR: " + str(exc))
        db.session.rollback()
        return ""
    try:
        # We never make it to here if the mb fails
        artist = release['artist-credit'][0]['artist']['name']
        logging.debug("artist=====" + str(artist))
        logging.debug("do have artwork?======" + str(release['cover-art-archive']['artwork']))
        # Get our front cover if it exists
        if get_cd_art(job, infos):
            logging.debug("we got an art image")
        else:
            logging.debug("we didnt get art image")
        # Set up the database properly for music cd's
        # job.logfile = clean_for_log(artist) + "_" + clean_for_log(release['title']) + ".log"
        artist_title = artist + " " + title
        args = {
            'job_id': str(job.job_id),
            'year': new_year,
            'year_auto': new_year,
            'title': artist_title,
            'title_auto': artist_title,
            'no_of_titles': infos['disc']['offset-count']
        }
        database_updater(args, job)
        # db.session.commit()
    except Exception as exc:
        artist_title = "Not identified" if not title else title
        logging.error("Try 2 -  ERROR: " + str(exc))
        db.session.rollback()
    return artist_title


def clean_for_log(s):
    a = str(s).replace(" ", "_")
    return a


def get_title(discid, job):
    """
    Ask musicbrainz.org for the release of the disc
    only gets the title of the album and artist

    arguments:
    discid - identification object from discid package
    job - the job object for the database entry

    return:
    the label of the disc as a string or "" if nothing was found

    Notes: dont try to use logging here -  doing so will break the arm setuplogging() function
    """
    mb.set_useragent("arm", "v1.0")
    try:
        infos = mb.get_releases_by_discid(discid, includes=['artist-credits'])
        logging.debug('mb info = %s', infos)
        title = str(infos['disc']['release-list'][0]['title'])
        logging.debug('title = %s', title)
        # Start setting our db stuff
        job.crc_id = str(infos['disc']['release-list'][0]['id'])
        logging.debug('crc = %s', job.crc_id)
        artist = str(infos['disc']['release-list'][0]['artist-credit'][0]['artist']['name'])
        logging.debug('artist = %s', artist)
        # log = clean_for_log(artist) + "_" + clean_for_log(title) + ".log"
        job.title = job.title_auto = artist + " " + title
        logging.debug('job.title = %s', job.title)
        job.video_type = "Music"
        clean_title = clean_for_log(artist) + "-" + clean_for_log(title)
        logging.debug('clean title = %s', clean_title)
        db.session.commit()
        return clean_title
        # return artist + "_" + title
    except mb.WebServiceError as exc:
        logging.error("mb.gettitle -  ERROR: " + str(exc))
        logging.debug('error = %s', str(exc))
        db.session.rollback()
        return "not identified"


def get_cd_art(job, infos):
    """
    Ask musicbrainz.org for the art of the disc

    arguments:
    job - the job object for the database entry
    infos - object/json returned from musicbrainz.org api

    return:
    True if we find the cd art
    False if we didnt find the art
    """
    try:
        # Use the build-in images from coverartarchive if available
        if infos['disc']['release-list'][0]['cover-art-archive']['artwork'] != "false":
            artlist = mb.get_image_list(job.crc_id)
            for image in artlist["images"]:
                # For verified images only
                """if "Front" in image["types"] and image["approved"]:
                    job.poster_url_auto = str(image["thumbnails"]["large"])
                    job.poster_url = str(image["thumbnails"]["large"])
                    return True"""
                # We dont care if its verified ?
                if "image" in image:
                    job.poster_url_auto = str(image["image"])
                    job.poster_url = str(image["image"])
                    return True
    except mb.WebServiceError as exc:
        db.session.rollback()
        logging.error("get_cd_art ERROR: " + str(exc))
    try:
        # This uses roboBrowser to grab the amazon/3rd party image if it exists
        browser = RoboBrowser(user_agent='a python robot')
        browser.open('https://musicbrainz.org/release/' + job.crc_id)
        img = browser.select('.cover-art img')
        # [<img src="https://images-eu.ssl-images-amazon.com/images/I/41SN9FK5ATL.jpg"/>]
        job.poster_url = re.search(r'<img src="(.*)"', str(img)).group(1)
        job.poster_url_auto = job.poster_url
        # logging.debug("img =====  " + str(img))
        # logging.debug("img stripped =====" + str(job.poster_url))
        db.session.commit()
        if job.poster_url != "":
            return True
        else:
            return False
    except mb.WebServiceError as exc:
        logging.error("get_cd_art ERROR: " + str(exc))
        db.session.rollback()
        return False


def database_updater(args, job, wait_time=90):
    """
    Try to update our db for x seconds and handle it nicely if we cant

    :param args:
    :param job:
    :param wait_time:
    :return:
    """
    # Loop through our args and try to set any of our job variables
    for (key, value) in args.items():
        logging.debug(str(key) + "= " + str(value))
        logging.debug("key = " + str(key))
        if key == "job_id":
            job.job_id = value
        elif key == "crc_id":
            job.crc_id = value
        elif key == "year":
            job.year = value
        elif key == "year_auto":
            job.year_auto = value
        elif key == "year_manual":
            job.year_manual = value
        elif key == "no_of_titles":
            job.no_of_titles = value
        elif key == "title":
            job.title = value
        elif key == "title_auto":
            job.title_auto = value
        elif key == "title_manual":
            job.title_manual = value
        elif key == "video_type":
            job.video_type = value
        elif key == "video_type_auto":
            job.video_type_auto = value
        elif key == "video_type_manual":
            job.video_type_manual = value
        elif key == "imdb_id":
            job.imdb_id = value
        elif key == "imdb_id_auto":
            job.poster_url = value
        elif key == "imdb_id_manual":
            job.imdb_id_manual = value
        elif key == "poster_url":
            job.poster_url = value
        elif key == "poster_url_auto":
            job.poster_url_auto = value
        elif key == "poster_url_manual":
            job.poster_url_manual = value
        elif key == "hasnicetitle":
            job.hasnicetitle = value

    for i in range(wait_time):  # give up after the users wait period in seconds
        try:
            db.session.commit()
        except Exception as e:
            # logging.debug("Exception = " + str(e) + "\n")
            if "locked" in str(e):
                time.sleep(1)
                logging.debug("database is locked - trying in 1 second")
            else:
                logging.debug("Error: " + str(e))
                db.session.rollback()
                time.sleep(1)
                job.status = "fail"
                db.session.commit()
                raise
        else:
            logging.debug("successfully written to the database")
            return True


if __name__ == "__main__":
    # this will break our logging if it ever triggers for arm
    # logging.basicConfig(level=logging.DEBUG)
    disc = Disc("/dev/cdrom")
    myid = get_disc_id(disc)
    logging.debug("DiscID: %s (%s)", str(myid), myid.freedb_id)
    logging.debug("URL: %s", myid.submission_url)
    logging.debug("Tracks: %s", myid.tracks)
    logging.debug("Musicbrain: %s", music_brainz(myid))
