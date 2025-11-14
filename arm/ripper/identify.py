#!/usr/bin/env python3
"""Identification of dvd/bluray"""

import os
import logging
import urllib
import re
import datetime
import unicodedata
import json
from ast import literal_eval

import pydvdid
import xmltodict
import arm.config.config as cfg

from arm.ripper import utils
from arm.ripper.ProcessHandler import arm_subprocess
from arm.ui import db

# flake8: noqa: W605
from arm.ui import utils as ui_utils


def check_if_mounted(mount_return_code, findmnt_return_code):
    """
    Function to check if mounting disc was success
     checking the return value of 2 linux shell functions;
     mount and findmnt.  mount can, in rare occasions,
     return no errors (0) yet still have not mounted
     the drive as expected.  findmnt, ran after the
     mount functions, confirms that the drive is indeed mounted.
     anything but 0 means we failed to mount disc
     :param mount_return_code: The return value of the linux "mount" function
     :param findmnt_return_code: The return value of the linux "findmnt" function
    """
    logging.debug(f"OS mounted value: {mount_return_code}")
    logging.debug(f"OS findmnt -M value: {findmnt_return_code}")
    success = False
    if mount_return_code == 0 and findmnt_return_code == 0:
        logging.info("Mounting disc was successful")
        success = True
    else:
        logging.error("Mounting failed! Rip might have problems")
    return success


def identify(job):
    """Identify disc attributes"""
    logging.debug("Identify Entry point --- job ----")
    logging.info(f"Mounting disc to: {job.mountpoint}")
    if not os.path.exists(str(job.mountpoint)):
        os.makedirs(str(job.mountpoint))
    # Check and mount drive - log error if failed
    mount_return_code = os.system(f"mount {job.mountpoint}")
    findmnt_return_code = os.system(f"findmnt -M {job.mountpoint}")
    mounted = check_if_mounted(mount_return_code, findmnt_return_code)
    # get_disc_type() checks local files, no need to run unless we can mount
    if mounted:
        # Check with the job class to get the correct disc type
        job.get_disc_type(utils.find_file("HVDVD_TS", job.mountpoint))

    if job.disctype in ["dvd", "bluray"]:

        logging.info("Disc identified as video")

        if cfg.arm_config["GET_VIDEO_TITLE"]:
            res = False
            if job.disctype == "dvd":
                res = identify_dvd(job)
            if job.disctype == "bluray":
                res = identify_bluray(job)
            if res:
                get_video_details(job)
            else:
                job.hasnicetitle = False
                db.session.commit()

            logging.info(f"Disc title Post ident -  title:{job.title} "
                         f"year:{job.year} video_type:{job.video_type} "
                         f"disctype: {job.disctype}")
            logging.debug(f"identify.job.end ---- \n\r{job.pretty_table()}")
    # No need to warn if we cant unmount
    os.system("umount " + job.devpath)


def identify_bluray(job):
    """ Get's Blu-Ray title by parsing XML in bdmt_eng.xml """

    try:
        with open(job.mountpoint + '/BDMV/META/DL/bdmt_eng.xml', "rb") as xml_file:
            doc = xmltodict.parse(xml_file.read())
    except OSError as error:
        logging.error("Disc is a bluray, but bdmt_eng.xml could not be found. "
                      "Disc cannot be identified.  Error "
                      f"number is: {error.errno}")
        # Maybe call OMdb with label when we can't find any ident on disc ?
        # Attempt to parse label
        if str(job.label) == "":
            job.title = str(job.label)
            job.year = ""
            db.session.commit()
            return False
        else:
            bluray_title = str(job.label)
            bluray_title = bluray_title.replace('_', ' ')
            bluray_title = bluray_title.title()
            job.title = job.title_auto = bluray_title
            job.year = ""
            db.session.commit()
            return True

    try:
        bluray_title = doc['disclib']['di:discinfo']['di:title']['di:name']
        if not bluray_title:
            bluray_title = job.label
    except KeyError:
        bluray_title = str(job.label)
        logging.error("Could not parse title from bdmt_eng.xml file.  Disc cannot be identified.")

    bluray_modified_timestamp = os.path.getmtime(job.mountpoint + '/BDMV/META/DL/bdmt_eng.xml')
    bluray_year = (datetime.datetime.fromtimestamp(bluray_modified_timestamp).strftime('%Y'))

    bluray_title = unicodedata.normalize('NFKD', str(bluray_title)).encode('ascii', 'ignore').decode()

    bluray_title = bluray_title.replace(' - Blu-rayTM', '')
    bluray_title = bluray_title.replace(' Blu-rayTM', '')
    bluray_title = bluray_title.replace(' - BLU-RAYTM', '')
    bluray_title = bluray_title.replace(' - BLU-RAY', '')
    bluray_title = bluray_title.replace(' - Blu-ray', '')

    bluray_title = utils.clean_for_filename(bluray_title)

    job.title = job.title_auto = bluray_title
    job.year = job.year_auto = bluray_year
    db.session.commit()

    return True


def identify_dvd(job):
    """ Manipulates the DVD title and calls OMDB to try and
    lookup the title """

    logging.debug(f"\n\r{job.pretty_table()}")
    # Some older DVDs aren't actually labelled
    if not job.label or job.label == "":
        job.label = "not identified"
    try:
        crc64 = pydvdid.compute(str(job.mountpoint))
        dvd_title = f"{job.label}_{crc64}"
        logging.info(f"DVD CRC64 hash is: {crc64}")
        job.crc_id = str(crc64)
        urlstring = f"https://1337server.pythonanywhere.com/api/v1/?mode=s&crc64={crc64}"
        logging.debug(urlstring)
        dvd_info_xml = urllib.request.urlopen(urlstring).read()
        arm_api_json = json.loads(dvd_info_xml)
        logging.debug(f"dvd xml - {arm_api_json}")
        logging.debug(f"results = {arm_api_json['results']}")
        if arm_api_json['success']:
            logging.info("Found crc64 id from online API")
            logging.info(f"title is {arm_api_json['results']['0']['title']}")
            args = {
                'title': arm_api_json['results']['0']['title'],
                'title_auto': arm_api_json['results']['0']['title'],
                'year': arm_api_json['results']['0']['year'],
                'year_auto': arm_api_json['results']['0']['year'],
                'imdb_id': arm_api_json['results']['0']['imdb_id'],
                'imdb_id_auto': arm_api_json['results']['0']['imdb_id'],
                'video_type': arm_api_json['results']['0']['video_type'],
                'video_type_auto': arm_api_json['results']['0']['video_type'],
                'poster_url': arm_api_json['results']['0']['poster_img'],
                'poster_url_auto': arm_api_json['results']['0']['poster_img'],
                'hasnicetitle': True
            }
            utils.database_updater(args, job)
    except Exception as error:
        logging.error(f"Pydvdid failed with the error: {error}")
        dvd_title = str(job.label)

    logging.debug(f"dvd_title_label: {dvd_title}")
    # in this block we want to strip out any chars that might be bad
    # strip all non-numeric chars and use that for year
    year = re.sub(r"\D", "", str(job.year)) if job.year else None
    # next line is not really needed, but we don't want to leave an x somewhere
    dvd_title = job.label.replace("16x9", "")
    logging.debug(f"dvd_title ^a-z _-: {dvd_title}")
    # rip out any SKU's at the end of the line
    dvd_title = re.sub(r"SKU\b", "", dvd_title)
    logging.debug(f"dvd_title SKU$: {dvd_title}")
    
    # Do we really need metaselector if we have got from ARM online db?
    try:
        dvd_info_xml = metadata_selector(job, dvd_title, year)
        logging.debug(f"DVD_INFO_XML: {dvd_info_xml}")
        identify_loop(job, dvd_info_xml, dvd_title, year)
    except Exception:
        dvd_info_xml = None
        logging.debug("Cant connect to online service!")
    # Failsafe so that we always have a title.
    if job.title is None or job.title == "None":
        job.title = str(job.label)
        job.year = None

    # Track 99 detection
    # -Oy means output a python dict
    output = arm_subprocess(["lsdvd", "-Oy", job.devpath])
    if output:
        try:
            # literal_eval only accepts literals so we have to adjust the output slightly
            tracks = literal_eval(re.sub(r"^.*\{", "{", output)).get("track", [])
            logging.debug(f"Detected {len(tracks)} tracks")
            if len(tracks) == 99:
                job.has_track_99 = True
                if cfg.arm_config["PREVENT_99"]:
                    raise Exception("Track 99 found and PREVENT_99 is enabled")
        except (SyntaxError, AttributeError) as e:
            logging.error("Failed to parse lsdvd output", exc_info=e)

    return True


def get_video_details(job):
    """ Clean up title and year.  Get video_type, imdb_id, poster_url from
    omdbapi.com webservice.\n

    job = Instance of Job class\n
    """
    title = job.title

    # Set out title from the job.label
    # return if not identified
    logging.debug(f"Title = {title}")
    if title == "not identified" or title is None or title == "":
        logging.info("Disc couldn't be identified")
        return
    title = re.sub('[_ ]', "+", title.strip())

    # strip all non-numeric chars and use that for year
    if job.year is None:
        year = ""
    else:
        year = re.sub(r"\D", "", str(job.year))

    logging.debug(f"Title: {title} | Year: {year}")
    logging.debug(f"Calling webservice with title: {title} and year: {year}")

    try:
        identify_loop(job, None, title, year)
    except Exception as error:
        logging.info(f"Identification failed with the error: {error}. Continuing...")


def update_job(job, search_results):
    """
    used to update a successfully found job
    :param job: job obj
    :param search_results: json returned from metadata provider
    :return: None if error
    """
    # logging.debug(f"s =======  {search_results}")
    if 'Search' not in search_results:
        return None
    new_year = search_results['Search'][0]['Year']
    title = utils.clean_for_filename(search_results['Search'][0]['Title'])
    logging.debug(f"Webservice successful.  New title is {title}.  New Year is: {new_year}")
    args = {
        'year_auto': str(new_year),
        'year': str(new_year),
        'title_auto': title,
        'title': title,
        'video_type_auto': search_results['Search'][0]['Type'],
        'video_type': search_results['Search'][0]['Type'],
        'imdb_id_auto': search_results['Search'][0]['imdbID'],
        'imdb_id': search_results['Search'][0]['imdbID'],
        'poster_url_auto': search_results['Search'][0]['Poster'],
        'poster_url': search_results['Search'][0]['Poster'],
        'hasnicetitle': True
    }
    return utils.database_updater(args, job)


def metadata_selector(job, title=None, year=None):
    """
    Used to switch between OMDB or TMDB as the metadata provider\n
    - TMDB returned queries are converted into the OMDB format

    :param job: The job class
    :param title: this can either be a search string or movie/show title
    :param year: the year of movie/show release

    :return: json/dict object or None
    """
    search_results = None
    if cfg.arm_config['METADATA_PROVIDER'].lower() == "tmdb":
        logging.debug("provider tmdb")
        search_results = ui_utils.tmdb_search(title, year)
        if search_results is not None:
            update_job(job, search_results)
    elif cfg.arm_config['METADATA_PROVIDER'].lower() == "omdb":
        logging.debug("provider omdb")
        search_results = ui_utils.call_omdb_api(str(title), str(year))
        if search_results is not None:
            update_job(job, search_results)
    else:
        logging.debug(cfg.arm_config['METADATA_PROVIDER'])
        logging.debug("unknown provider - doing nothing, saying nothing. Getting Kryten")
    return search_results


def identify_loop(job, response, title, year):
    """

    :param job:
    :param response:
    :param title:
    :param year:
    """
    # handle failures
    # this is a little kludgy, but it kind of works...
    logging.debug(f"Response = {response}")
    if response is None:
        # try with year first
        response = try_with_year(job, response, title, year)
        # try submitting without the year
        response = try_without_year(job, response, title)

        if response is None:
            while response is None and title.find("-") > 0:
                title = title.rsplit('-', 1)[0]
                logging.debug(f"Trying title: {title}")
                response = metadata_selector(job, title, year)
                logging.debug(f"response: {response}")

            # if still fail, then try slicing off the last word in a loop
            while response is None and title.count('+') > 0:
                title = title.rsplit('+', 1)[0]
                logging.debug(f"Trying title: {title}")
                response = metadata_selector(job, title, year)
                logging.debug(f"response: {response}")
                if response is None:
                    # Still failing - try the words we have without year
                    logging.debug("Removing year...")
                    response = metadata_selector(job, title)


def try_without_year(job, response, title):
    """

    :param job:
    :param response:
    :param title:
    :return:
    """
    if response is None:
        logging.debug("Removing year...")
        response = metadata_selector(job, title)
        logging.debug(f"response: {response}")
    return response


def try_with_year(job, response, title, year):
    """

    :param job:
    :param response:
    :param title:
    :param year:
    :return:
    """
    # If we have a response don't overwrite it
    if response is not None:
        return response
    if year:
        response = metadata_selector(job, title, str(year))
        logging.debug(f"response: {response}")
    # If we still don't have a response try removing a year off
    if response is None and year:
        # This accounts for when
        # the dvd release date is the year following the movie release date
        logging.debug("Subtracting 1 year...")
        response = metadata_selector(job, title, str(int(year) - 1))
    return response
