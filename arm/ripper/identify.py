#!/usr/bin/env python3
# Identification of dvd/bluray

import os
import sys  # noqa # pylint: disable=unused-import
import logging
import urllib
import re
import datetime
import pydvdid
import unicodedata
import xmltodict
import json

from arm.ripper import utils
from arm.ui import db
from arm.config.config import cfg


# flake8: noqa: W605
# from arm.ui.utils import call_omdb_api, tmdb_search
import arm.ui.utils as u


def identify(job, logfile):
    """Identify disc attributes"""

    logging.debug(f"Identify Entry point --- job ---- \n\r{job.pretty_table()}")
    logging.info(f"Mounting disc to: {job.mountpoint}")

    if not os.path.exists(str(job.mountpoint)):
        os.makedirs(str(job.mountpoint))

    os.system("mount " + job.devpath)

    # Check with the job class to get the correct disc type
    job.get_disc_type(utils.find_file("HVDVD_TS", job.mountpoint))

    if job.disctype in ["dvd", "bluray"]:

        logging.info("Disc identified as video")

        if cfg["GET_VIDEO_TITLE"]:
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

            logging.info(f"Disc title Post ident -  title:{job.title} year:{job.year} video_type:{job.video_type} "
                         f"disctype: {job.disctype}")
            logging.debug(f"identify.job.end ---- \n\r{job.pretty_table()}")

    os.system("umount " + job.devpath)


def clean_for_filename(string):
    """ Cleans up string for use in filename """
    string = re.sub('\\[(.*?)\\]', '', string)
    string = re.sub('\\s+', ' ', string)
    string = string.replace(' : ', ' - ')
    string = string.replace(':', '-')
    string = string.replace('&', 'and')
    string = string.replace("\\", " - ")
    string = string.strip()
    return re.sub('[^\\w_.() -]', '', string)


def identify_bluray(job):
    """ Get's Blu-Ray title by parsing XML in bdmt_eng.xml """

    try:
        with open(job.mountpoint + '/BDMV/META/DL/bdmt_eng.xml', "rb") as xml_file:
            doc = xmltodict.parse(xml_file.read())
    except OSError as e:
        logging.error("Disc is a bluray, but bdmt_eng.xml could not be found.  Disc cannot be identified.  Error "
                      "number is: " + str(e.errno))
        # Maybe call OMdb with label when we cant find any ident on disc ?
        job.title = str(job.label)
        job.year = ""
        db.session.commit()
        return False

    try:
        bluray_title = doc['disclib']['di:discinfo']['di:title']['di:name']
    except KeyError:
        bluray_title = str(job.label)
        bluray_year = ""
        logging.error("Could not parse title from bdmt_eng.xml file.  Disc cannot be identified.")

    bluray_modified_timestamp = os.path.getmtime(job.mountpoint + '/BDMV/META/DL/bdmt_eng.xml')
    bluray_year = (datetime.datetime.fromtimestamp(bluray_modified_timestamp).strftime('%Y'))

    bluray_title = unicodedata.normalize('NFKD', bluray_title).encode('ascii', 'ignore').decode()

    bluray_title = bluray_title.replace(' - Blu-rayTM', '')
    bluray_title = bluray_title.replace(' Blu-rayTM', '')
    bluray_title = bluray_title.replace(' - BLU-RAYTM', '')
    bluray_title = bluray_title.replace(' - BLU-RAY', '')
    bluray_title = bluray_title.replace(' - Blu-ray', '')

    bluray_title = clean_for_filename(bluray_title)

    job.title = job.title_auto = bluray_title
    job.year = job.year_auto = bluray_year
    db.session.commit()

    return True


def identify_dvd(job):
    """ Manipulates the DVD title and calls OMDB to try and
    lookup the title """

    logging.debug("\n\r" + job.pretty_table())
    # Some older DVDs aren't actually labelled
    if not job.label or job.label == "":
        job.label = "not identified"
    try:
        crc64 = pydvdid.compute(str(job.mountpoint))
        fallback_title = f"{job.label}_{crc64}"
        dvd_title = fallback_title
        logging.info(f"DVD CRC64 hash is: {crc64}")
        job.crc_id = str(crc64)
        urlstring = f"http://1337server.pythonanywhere.com/api/v1/?mode=s&crc64={crc64}"
        logging.debug(urlstring)
        dvd_info_xml = urllib.request.urlopen(urlstring).read()
        x = json.loads(dvd_info_xml)
        logging.debug("dvd xml - " + str(x))
        logging.debug(f"results = {x['results']}")
        if bool(x['success']):
            logging.info("Found crc64 id from online API")
            logging.info(f"title is {x['results']['0']['title']}")
            args = {
                    'title': x['results']['0']['title'],
                    'title_auto': x['results']['0']['title'],
                    'year': x['results']['0']['year'],
                    'year_auto': x['results']['0']['year'],
                    'imdb_id': x['results']['0']['imdb_id'],
                    'imdb_id_auto': x['results']['0']['imdb_id'],
                    'video_type': x['results']['0']['video_type'],
                    'video_type_auto': x['results']['0']['video_type'],
                    }
            utils.database_updater(args, job)
            # return True
    except Exception as e:
        logging.error("Pydvdid failed with the error: " + str(e))
        dvd_title = fallback_title = str(job.label)

    logging.debug("dvd_title_label= " + str(dvd_title))
    # strip all non-numeric chars and use that for year
    year = re.sub(r"[^0-9]", "", str(job.year))
    # next line is not really needed, but we dont want to leave an x somewhere
    dvd_title = job.label.replace("16x9", "")
    # Rip out any not alpha chars replace with &nbsp;
    dvd_title = re.sub(r"[^a-zA-Z ]", " ", dvd_title)
    logging.debug("dvd_title ^a-z= " + str(dvd_title))
    # rip out any SKU's at the end of the line
    dvd_title = re.sub(r"SKU\b", "", dvd_title)
    logging.debug("dvd_title SKU$= " + str(dvd_title))

    dvd_info_xml = metadata_selector(job, dvd_title, year)
    logging.debug("DVD_INFO_XML: " + str(dvd_info_xml))
    # Failsafe so they we always have a title.
    if job.title is None or job.title == "None":
        job.title = str(job.label)
        job.year = ""
    return True


def get_video_details(job):
    """ Clean up title and year.  Get video_type, imdb_id, poster_url from
    omdbapi.com webservice.\n

    job = Instance of Job class\n
    """
    title = job.title

    # Set out title from the job.label
    # return if not identified
    logging.debug("Title = " + str(title))
    if title == "not identified" or title is None or title == "":
        logging.info("Disc couldn't be identified")
        return
    title = re.sub('[_ ]', "+", title.strip())

    # strip all non-numeric chars and use that for year
    if job.year is None:
        year = ""
    else:
        year = re.sub("[^0-9]", "", str(job.year))

    logging.debug(f"Title: {title} | Year: {year}")
    logging.debug(f"Calling webservice with title: {title} and year: {year}")

    response = metadata_selector(job, title, year)

    # handle failures
    # this is a little kludgy, but it kind of works...
    if response is None:
        if year:
            # first try subtracting one year.  This accounts for when
            # the dvd release date is the year following the movie release date
            logging.debug("Subtracting 1 year...")
            response = metadata_selector(job, title, str(int(year) - 1))
            logging.debug(f"response: {response}")

        # try submitting without the year
        if response is None:
            logging.debug("Removing year...")
            response = metadata_selector(job, title)
            logging.debug(f"response: {response}")

        if response is None:
            while response is None and title.find("-") > 0:
                title = title.rsplit('-', 1)[0]
                logging.debug("Trying title: " + title)
                response = metadata_selector(job, title, year)
                logging.debug(f"response: {response}")

            # if still fail, then try slicing off the last word in a loop
            while response is None and title.count('+') > 0:
                title = title.rsplit('+', 1)[0]
                logging.debug("Trying title: " + title)
                response = metadata_selector(job, title, year)
                logging.debug(f"response: {response}")
                if response is None:
                    logging.debug("Removing year...")
                    response = metadata_selector(job, title)


def update_job(job, s):
    logging.debug(f"s =======  {s}")
    if 'Search' not in s:
        return None
    new_year = s['Search'][0]['Year']
    title = clean_for_filename(s['Search'][0]['Title'])
    logging.debug("Webservice successful.  New title is " + title + ".  New Year is: " + new_year)
    args = {
        'year_auto': str(new_year),
        'year': str(new_year),
        'title_auto': title,
        'title': title,
        'video_type_auto': s['Search'][0]['Type'],
        'video_type': s['Search'][0]['Type'],
        'imdb_id_auto': s['Search'][0]['imdbID'],
        'imdb_id': s['Search'][0]['imdbID'],
        'poster_url_auto': s['Search'][0]['Poster'],
        'poster_url': s['Search'][0]['Poster'],
        'hasnicetitle': True
    }
    utils.database_updater(args, job)


def metadata_selector(job, title=None, year=None):
    """
    Used to switch between OMDB or TMDB as the metadata provider
    - TMDB returned queries are converted into the OMDB format

    :param job: The job class
    :param title: this can either be a search string or movie/show title
    :param year: the year of movie/show release

    :return: json/dict object or None

    Args:
        job:
    """
    if cfg['METADATA_PROVIDER'].lower() == "tmdb":
        logging.debug("provider tmdb")
        x = u.tmdb_search(title, year)
        if x is not None:
            update_job(job, x)
        return x
    elif cfg['METADATA_PROVIDER'].lower() == "omdb":
        logging.debug("provider omdb")
        x = u.call_omdb_api(str(title), str(year))
        if x is not None and x['Response']:
            update_job(job, x)
        return x
    logging.debug(cfg['METADATA_PROVIDER'])
    logging.debug("unknown provider - doing nothing, saying nothing. Getting Kryten")
