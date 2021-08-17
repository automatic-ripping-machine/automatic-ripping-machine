#!/usr/bin/env python3
import logging
import re
import musicbrainzngs as mb
from discid import read, Disc

from arm.config.config import cfg
import arm.ripper.utils as u
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
        u.database_updater(args, job)
        logging.debug("musicbrain works -  New title is " + title + ".  New Year is: " + new_year)
    except mb.WebServiceError as exc:
        logging.error("Cant reach MB or cd not found ? - ERROR: " + str(exc))
        u.database_updater(False, job)
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
        artist_title = artist + " " + title
        args = {
            'job_id': str(job.job_id),
            'year': new_year,
            'year_auto': new_year,
            'title': artist_title,
            'title_auto': artist_title,
            'no_of_titles': infos['disc']['offset-count']
        }
        u.database_updater(args, job)
    except Exception as exc:
        artist_title = "Not identified" if not title else title
        logging.error("Try 2 -  ERROR: " + str(exc))
        u.database_updater(False, job)
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

    Notes: dont try to use logging here -  doing so will break the arm setup_logging() function
    """
    mb.set_useragent("arm", "v1.0")
    try:
        infos = mb.get_releases_by_discid(discid, includes=['artist-credits'])
        title = str(infos['disc']['release-list'][0]['title'])
        # Start setting our db stuff
        artist = str(infos['disc']['release-list'][0]['artist-credit'][0]['artist']['name'])
        clean_title = clean_for_log(artist) + "-" + clean_for_log(title)
        args = {
            'crc_id': str(infos['disc']['release-list'][0]['id']),
            'title': str(artist + " " + title),
            'title_auto': str(artist + " " + title),
            'video_type': "Music"
        }
        u.database_updater(args, job)
        return clean_title
    except mb.WebServiceError:
        u.database_updater(False, job)
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
                    args = {
                        'poster_url': str(image["image"]),
                        'poster_url_auto': str(image["image"])
                    }
                    u.database_updater(args, job)
                    return True
    except mb.WebServiceError as exc:
        u.database_updater(False, job)
        logging.error("get_cd_art ERROR: " + str(exc))
    try:
        # This uses roboBrowser to grab the amazon/3rd party image if it exists
        browser = RoboBrowser(user_agent='ARM-v2_devel')
        browser.open('https://musicbrainz.org/release/' + job.crc_id)
        img = browser.select('.cover-art img')
        # [<img src="https://images-eu.ssl-images-amazon.com/images/I/41SN9FK5ATL.jpg"/>]
        # img[0].text
        args = {
            'poster_url': str(re.search(r'<img src="(.*)"', str(img)).group(1)),
            'poster_url_auto': str(re.search(r'<img src="(.*)"', str(img)).group(1)),
            'video_type': "Music"
        }
        u.database_updater(args, job)
        if job.poster_url != "":
            return True
        else:
            return False
    except mb.WebServiceError as exc:
        logging.error("get_cd_art ERROR: " + str(exc))
        u.database_updater(False, job)
        return False


if __name__ == "__main__":
    # this will break our logging if it ever triggers for arm
    disc = Disc("/dev/cdrom")
    myid = get_disc_id(disc)
    logging.debug("DiscID: %s (%s)", str(myid), myid.freedb_id)
    logging.debug("URL: %s", myid.submission_url)
    logging.debug("Tracks: %s", myid.tracks)
    logging.debug("Musicbrain: %s", music_brainz(myid, None))
