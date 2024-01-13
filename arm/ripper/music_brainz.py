#!/usr/bin/env python3
"""Module to connect to A.R.M to MusicBrainz API"""

import logging
import re
import musicbrainzngs as mb
import arm.config.config as cfg

from discid import read, Disc

from arm.ripper import utils as u
import werkzeug

werkzeug.cached_property = werkzeug.utils.cached_property


def main(disc):
    """
    Depending on the configuration musicbrainz is used
    to identify the music disc. The label of the disc is returned
    or "".
    """
    discid = get_disc_id(disc)
    if cfg.arm_config['GET_AUDIO_TITLE'] == 'musicbrainz':
        return music_brainz(discid, disc)
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
    :param discid: identification object from discid package
    :param job: the job class/obj
    :return: the label of the disc as a string or "" if nothing was found
    """
    mb.set_useragent("arm", "v2_devel")
    try:
        infos = mb.get_releases_by_discid(discid, includes=['artist-credits', 'recordings'])
        logging.debug(f"Infos: {infos}")
        logging.debug(f"discid = {discid}")
        if 'disc' in infos:
            process_tracks(job, infos['disc']['release-list'][0]['medium-list'][0]['track-list'])
            logging.debug("-" * 300)
            release = infos['disc']['release-list'][0]
            new_year = check_date(release)
            title = str(release.get('title', 'no title'))
            # Set out release id as the CRC_ID
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
            logging.debug(f"musicbrain works -  New title is {title}  New Year is: {new_year}")
        elif 'cdstub' in infos:
            process_tracks(job, infos['cdstub']['track-list'], is_stub=True)
            title = str(infos['cdstub']['title'])
            args = {
                'job_id': str(job.job_id),
                'crc_id': infos['cdstub']['id'],
                'hasnicetitle': True,
                'title': title,
                'title_auto': title
            }
            u.database_updater(args, job)
            logging.debug(f"musicbrain works, but stubbed -  New title is {title}")
            if 'artist' in infos['cdstub']:
                artist = infos['cdstub']['artist']
                args = {
                    'job_id': str(job.job_id),
                    'crc_id': infos['cdstub']['id'],
                    'hasnicetitle': True,
                    'title': artist + " " + title,
                    'title_auto': artist + " " + title
                }
                u.database_updater(args, job)
    except mb.WebServiceError as exc:
        logging.error(f"Cant reach MB or cd not found ? - ERROR: {exc}")
        u.database_updater(False, job)
        return ""
    try:
        # We never make it to here if the mb fails
        if 'disc' in infos:
            artist = release['artist-credit'][0]['artist']['name']
            no_of_titles = infos['disc']['offset-count']
        elif 'cdstub' in infos:
            artist = infos['cdstub']['artist']
            no_of_titles = infos['cdstub']['track-count']
            new_year = ''

        logging.debug(f"artist====={artist}")
        if 'disc' in infos:
            logging.debug(f"do have artwork?======{release['cover-art-archive']['artwork']}")
        elif 'cdstub' in infos:
            logging.debug("do have artwork?======No (cdstub)")
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
            'no_of_titles': no_of_titles
        }
        u.database_updater(args, job)
    except Exception as exc:
        artist_title = "Not identified" if not title else title
        logging.error(f"Try 2 -  ERROR: {exc}")
        u.database_updater(False, job)
    return artist_title


def check_date(release):
    """
    Check for valid date
    :param release:
    :return: correct year
    """
    # Clean up the date and the title
    if 'date' in release:
        new_year = str(release['date'])
        new_year = re.sub(r"-\d{2}-\d{2}$", "", new_year)
    else:
        # sometimes there is no date in a release
        new_year = ""
    return new_year


def get_title(discid, job):
    """
    Ask musicbrainz.org for the release of the disc
    only gets the title of the album and artist

    :param discid: identification object from discid package
    :param job: the job object for the database entry
    :return: the label of the disc as a string or "" if nothing was found

    Notes: dont try to use logging here -  doing so will break the arm setup_logging() function
    """
    mb.set_useragent("arm", "v2_devel")
    try:
        infos = mb.get_releases_by_discid(discid, includes=['artist-credits'])
        logging.debug(f"Infos: {infos}")
        logging.debug(f"discid = {discid}")
        if 'disc' in infos:
            title = str(infos['disc']['release-list'][0]['title'])
            # Start setting our db stuff
            artist = str(infos['disc']['release-list'][0]['artist-credit'][0]['artist']['name'])
            crc_id = str(infos['disc']['release-list'][0]['id'])
        elif 'cdstub' in infos:
            title = str(infos['cdstub']['title'])
            artist = str(infos['cdstub']['artist'])
            # Different id format, but what can you do?
            crc_id = str(infos['cdstub']['id'])
        else:
            u.database_updater(False, job)
            return "not identified"

        clean_title = u.clean_for_filename(artist) + "-" + u.clean_for_filename(title)
        args = {
            'crc_id': crc_id,
            'title': str(artist + " " + title),
            'title_auto': str(artist + " " + title),
            'video_type': "Music"
        }
        u.database_updater(args, job)
        return clean_title
    except (mb.WebServiceError, KeyError):
        u.database_updater(False, job)
        return "not identified"


def get_cd_art(job, infos):
    """
    Ask musicbrainz.org for the art of the disc

    :param job: the job object for the database entry
    :param infos: object/json returned from musicbrainz.org api
    :return:     True if we find the cd art - False if we didnt find the art
    """
    try:
        # Use the build-in images from coverartarchive if available
        if 'disc' in infos:
            release_list = infos['disc']['release-list']
            first_release_with_artwork = next(
                (release for release in release_list if release.get('cover-art-archive', {}).get('artwork') != "false"),
                None
            )

            if first_release_with_artwork is not None:
                artlist = mb.get_image_list(first_release_with_artwork['id'])
                for image in artlist["images"]:
                    # We dont care if its verified ?
                    if "image" in image:
                        args = {
                            'poster_url': str(image["image"]),
                            'poster_url_auto': str(image["image"])
                        }
                        u.database_updater(args, job)
                        return True
        return False
    except mb.WebServiceError as exc:
        u.database_updater(False, job)
        logging.error(f"get_cd_art ERROR: {exc}")
        return False


def process_tracks(job, mb_track_list, is_stub=False):
    """

    :param job:
    :param mb_track_list:
    :param is_stub:
    :return:
    """
    for (idx, track) in enumerate(mb_track_list):
        track_leng = 0
        try:
            if is_stub:
                track_leng = int(track['length'])
            else:
                track_leng = int(track['recording']['length'])
        except ValueError:
            logging.error("Failed to find track length")
        trackno = track.get('number', idx + 1)
        if is_stub:
            title = track.get('title', f"Untitled track {trackno}")
        else:
            title = track['recording']['title']
        u.put_track(job, trackno, track_leng, "n/a", 0.1, False, "ABCDE", title)


if __name__ == "__main__":
    # this will break our logging if it ever triggers for arm
    disc = Disc("/dev/cdrom")
    myid = get_disc_id(disc)
    logging.debug("DiscID: %s (%s)", str(myid), myid.freedb_id)
    logging.debug("URL: %s", myid.submission_url)
    logging.debug("Tracks: %s", myid.tracks)
    logging.debug("Musicbrain: %s", music_brainz(myid, None))
