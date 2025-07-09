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

    # Tell musicbrainz what your app is, and how to contact you
    # (this step is required, as per the webservice access rules
    # at http://wiki.musicbrainz.org/XML_Web_Service/Rate_Limiting )
    mb.set_useragent(app="arm", version=str(job.arm_version), contact="https://github.com/automatic-ripping-machine")

    # Get CD info from musicbrainz and catch any errors
    try:
        disc_info = mb.get_releases_by_discid(discid, includes=['artist-credits', 'recordings'])
        logging.debug(f"discid: [{discid}]")
        # Debugging, will dump the entire xml/json data from musicbrainz
        #logging.debug(f"disc_info: {disc_info}")

    except mb.WebServiceError as exc:
        logging.error(f"Cant reach MB or cd not found ? - ERROR: {exc}")
        u.database_updater(False, job)
        return ""

    # The following will only run when musicbrainz returns data
    if 'disc' in disc_info:
        logging.debug("Processing as a disc")
        release_list = disc_info['disc'].get('release-list', [])
        logging.debug(f"Number of releases: {len(release_list)}")

        # Check returned data has a release_list (album release info), otherwise return empty
        if len(release_list) > 0:
            # Loop through release data and find first that is a CD
            for i in range(len(release_list)):
                logging.debug(f"Checking release: [{i}] if CD")
                medium_list = release_list[i].get('medium-list', [])
                # Check that medium_list is valid (has data) and that we have returned a CD
                # possible values are "12' Vinyl" or "CD" from testing
                if medium_list and medium_list[0].get('format') == "CD":
                    logging.debug(f"Release [{i}] is a CD, tracking on...")
                    logging.debug("-" * 50)
                    process_tracks(job, medium_list[0].get('track-list'))
                    logging.debug("-" * 50)
                    release = disc_info['disc']['release-list'][i]
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

        else:
            # Return nothing, the returned data has no release_list
            logging.error("No release information reported by MusicBrainz")
            return ""

    # Run if not a disc, but a cdstub (limited data)
    # No check on release is done here, assuming cdstub is limited to CDs
    elif 'cdstub' in disc_info:
        logging.debug("Processing as a cdstub")
        process_tracks(job, disc_info['cdstub']['track-list'], is_stub=True)
        title = str(disc_info['cdstub']['title'])
        args = {
            'job_id': str(job.job_id),
            'crc_id': disc_info['cdstub']['id'],
            'hasnicetitle': True,
            'title': title,
            'title_auto': title
        }
        u.database_updater(args, job)
        logging.debug(f"musicbrain works, but stubbed -  New title is {title}")
        if 'artist' in disc_info['cdstub']:
            artist = disc_info['cdstub']['artist']
            args = {
                'job_id': str(job.job_id),
                'crc_id': disc_info['cdstub']['id'],
                'hasnicetitle': True,
                'title': artist + " " + title,
                'title_auto': artist + " " + title
            }
            u.database_updater(args, job)

    try:
        if 'disc' in disc_info:
            artist = release['artist-credit'][0]['artist']['name']
            no_of_titles = disc_info['disc']['offset-count']
        elif 'cdstub' in disc_info:
            artist = disc_info['cdstub']['artist']
            no_of_titles = disc_info['cdstub']['track-count']
            new_year = ''

        logging.debug(f"artist====={artist}")
        if 'disc' in disc_info:
            logging.debug(f"do have artwork?======{release['cover-art-archive']['artwork']}")
        elif 'cdstub' in disc_info:
            logging.debug("do have artwork?======No (cdstub)")
        # Get our front cover if it exists
        if get_cd_art(job, disc_info):
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

    Notes: dont try to use logging here - doing so will break the arm setup_logging() function
    """

    # Tell musicbrainz what your app is, and how to contact you
    # (this step is required, as per the webservice access rules
    # at http://wiki.musicbrainz.org/XML_Web_Service/Rate_Limiting )
    mb.set_useragent("arm", version=str(job.arm_version), contact="https://github.com/automatic-ripping-machine")
    try:
        disc_info = mb.get_releases_by_discid(discid, includes=['artist-credits'])
        logging.debug(f"disc_info: {disc_info}")
        logging.debug(f"discid = {discid}")
        if 'disc' in disc_info:
            title = str(disc_info['disc']['release-list'][0]['title'])
            # Start setting our db stuff
            artist = str(disc_info['disc']['release-list'][0]['artist-credit'][0]['artist']['name'])
            crc_id = str(disc_info['disc']['release-list'][0]['id'])
        elif 'cdstub' in disc_info:
            title = str(disc_info['cdstub']['title'])
            artist = str(disc_info['cdstub']['artist'])
            # Different id format, but what can you do?
            crc_id = str(disc_info['cdstub']['id'])
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


def get_cd_art(job, disc_info):
    """
    Ask musicbrainz.org for the art of the disc

    :param job: the job object for the database entry
    :param disc_info: object/json returned from musicbrainz.org api
    :return:     True if we find the cd art - False if we didnt find the art
    """
    try:
        # Use the build-in images from coverartarchive if available
        if 'disc' in disc_info:
            release_list = disc_info['disc']['release-list']
            logging.debug(f"release_list: {release_list}")
            first_release_with_artwork = next(
                (release for release in release_list if release.get('cover-art-archive', {}).get('artwork') != "false"),
                None
            )
            logging.debug(f"first_release_with_artwork: {first_release_with_artwork}")

            if first_release_with_artwork is not None:
                # Call function from https://python-musicbrainzngs.readthedocs.io/en/v0.7/api/#musicbrainzngs.get_image_list
                # 400: Releaseid is not a valid UUID
                # 404: No release exists with an MBID of releaseid
                # 503: Ratelimit exceeded
                artlist = mb.get_image_list(first_release_with_artwork['id'])
                logging.debug(f"artlist: {artlist}")

                for image in artlist["images"]:
                    # We dont care if its verified ?
                    if "image" in image:
                        args = {
                            'poster_url': str(image["image"]),
                            'poster_url_auto': str(image["image"])
                        }
                        u.database_updater(args, job)
                        logging.debug(f"poster_url: {args['poster_url']} poster_url_auto: {args['poster_url_auto']}")
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
