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

from arm.ripper import getmusictitle
from arm.ripper import utils
from arm.ui import db

# from arm.config.config import cfg

# flake8: noqa: W605


def identify(job, logfile):
    """Identify disc attributes"""

    logging.debug("Identify Entry point --- job ---- \n\r" + job.pretty_table())
    logging.info("Mounting disc to: " + str(job.mountpoint))

    if not os.path.exists(str(job.mountpoint)):
        os.makedirs(str(job.mountpoint))

    os.system("mount " + job.devpath)

    # Check to make sure it's not a data disc
    if job.disctype == "music":
        logging.debug("Disc is music.")
        job.label = getmusictitle.main(job)
    elif os.path.isdir(job.mountpoint + "/VIDEO_TS"):
        logging.debug("Found: " + job.mountpoint + "/VIDEO_TS")
        job.disctype = "dvd"
    elif os.path.isdir(job.mountpoint + "/video_ts"):
        logging.debug("Found: " + job.mountpoint + "/video_ts")
        job.disctype = "dvd"
    elif os.path.isdir(job.mountpoint + "/BDMV"):
        logging.debug("Found: " + job.mountpoint + "/BDMV")
        job.disctype = "bluray"
    elif os.path.isdir(job.mountpoint + "/HVDVD_TS"):
        logging.debug("Found: " + job.mountpoint + "/HVDVD_TS")
        # do something here
    elif utils.find_file("HVDVD_TS", job.mountpoint):
        logging.debug("Found file: HVDVD_TS")
        # do something here too
    else:
        logging.debug("Did not find valid dvd/bd files. Changing disctype to 'data'")
        job.disctype = "data"

    if job.disctype in ["dvd", "bluray"]:

        logging.info("Disc identified as video")

        if job.config.GET_VIDEO_TITLE:
            # get crc_id (dvd only), title, year
            if job.disctype == "dvd":
                res = identify_dvd(job)
            if job.disctype == "bluray":
                res = identify_bluray(job)
            # Need to check if year is "0000"  or ""
            if res and job.year != "0000":
                get_video_details(job)
            else:
                job.hasnicetitle = False
                db.session.commit()

            logging.info(
                "Disc title Post ident: " + str(job.title) + " : " + str(job.year) + " : " + str(job.video_type))
            logging.debug("identify.job.end ---- \n\r" + job.pretty_table())
            
    os.system("umount " + job.devpath)


def clean_for_filename(string):
    """ Cleans up string for use in filename """
    string = re.sub('\[(.*?)\]', '', string)
    string = re.sub('\s+', ' ', string)
    string = string.replace(' : ', ' - ')
    string = string.replace(':', '-')
    # Added from pull 366
    string = string.replace('&', 'and')
    string = string.replace("\\", " - ")
    string = string.strip()

    # Added from pull 366
    # testing why the return function isn't cleaning
    return re.sub('[^\w\-_\.\(\) ]', '', string)
    # return string


def identify_bluray(job):
    """ Get's Blu-Ray title by parsing XML in bdmt_eng.xml """

    try:
        with open(job.mountpoint + '/BDMV/META/DL/bdmt_eng.xml', "rb") as xml_file:
            doc = xmltodict.parse(xml_file.read())
    except OSError as e:
        logging.error("Disc is a bluray, but bdmt_eng.xml could not be found.  Disc cannot be identified.  Error "
                      "number is: " + str(e.errno))
        # job.title = "not identified"
        job.title = str(job.label)
        job.year = ""
        db.session.commit()
        return False

    try:
        bluray_title = doc['disclib']['di:discinfo']['di:title']['di:name']
    except KeyError:
        # Changed from pull 366
        # bluray_title = "not identified"
        bluray_title = str(job.label)
        bluray_year = ""
        logging.error("Could not parse title from bdmt_eng.xml file.  Disc cannot be identified.")
        # return False

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
    # Added from #338
    # Some older DVDs aren't actually labelled
    if not job.label or job.label == "":
        job.label = "not identified"

    dvd_info_xml = False
    dvd_release_date = ""

    # TODO: remove this because its pointless keeping when it can never work
    try:
        crc64 = pydvdid.compute(str(job.mountpoint))
        fallback_title = "{0}_{1}".format(str(job.label), str(crc64))
        dvd_title = str(fallback_title)
        logging.info("DVD CRC64 hash is: " + str(crc64))
        job.crc_id = str(crc64)
        # Dead needs removing
        urlstring = "http://metaservices.windowsmedia.com/pas_dvd_B/template/GetMDRDVDByCRC.xml?CRC={0}".format(
            str(crc64))
        logging.debug(urlstring)
    except pydvdid.exceptions.PydvdidException as e:
        logging.error("Pydvdid failed with the error: " + str(e))
        dvd_title = fallback_title = str(job.label)

    dvd_title = job.label
    logging.debug("dvd_title_label= " + str(dvd_title))
    # strip all non-numeric chars and use that for year
    year = re.sub("[^0-9]", "", str(job.year))
    # next line is not really needed, but we dont want to leave an x somewhere
    dvd_title = job.label.replace("16x9", "")
    # Rip out any not alpha chars replace with
    dvd_title = re.sub("[^a-zA-Z ]", " ", dvd_title)
    logging.debug("dvd_title ^a-z= " + str(dvd_title))
    # rip out any SKU's at the end of the line
    dvd_title = re.sub("SKU$", " ", dvd_title)
    logging.debug("dvd_title SKU$= " + str(dvd_title))

    # try to contact omdb
    try:
        dvd_info_xml = callwebservice(job, job.config.OMDB_API_KEY, dvd_title, year)
        logging.debug("DVD_INFO_XML: " + str(dvd_info_xml))
    except OSError as e:
        # we couldnt reach omdb
        logging.error("Failed to reach OMDB")
        return False

    job.year = year
    job.title = dvd_title
    db.session.commit()
    return True


def get_video_details(job):
    """ Clean up title and year.  Get video_type, imdb_id, poster_url from
    omdbapi.com webservice.\n

    job = Instance of Job class\n
    """
    # Make sure we have a title.
    # if we do its bluray use job.title not job.label
    try:
        if job.title is not None and job.title != "":
            title = str(job.title)
        else:
            title = str(job.label)
    except TypeError:
        title = str(job.label)

    # Set out title from the job.label
    # return if not identified
    logging.debug("Title = " + title)
    if title == "not identified" or title is None:
        return
    # dvd_title_clean = cleanupstring(dvd_title)
    title = title.strip()
    title = re.sub('[_ ]', "+", title)

    # strip all non-numeric chars and use that for year
    if job.year is None:
        year = ""
    else:
        year = str(job.year)
        year = re.sub("[^0-9]", "", year)

    omdb_api_key = job.config.OMDB_API_KEY

    logging.debug("Title: " + title + " | Year: " + year)
    logging.debug("Calling webservice with title: " + title + " and year: " + year)

    # Callwebservice already handles commiting to database, no need for identify_dvd()
    response = callwebservice(job, omdb_api_key, title, year)
    logging.debug("response: " + str(response))

    # handle failures
    # this is a little kludgy, but it kind of works...
    if (response == "fail"):
        if year:
            # first try subtracting one year.  This accounts for when
            # the dvd release date is the year following the movie release date
            logging.debug("Subtracting 1 year...")
            response = callwebservice(job, omdb_api_key, title, str(int(year) - 1))
            logging.debug("response: " + str(response))

        # try submitting without the year
        if response == "fail":
            # year needs to be changed
            logging.debug("Removing year...")
            response = callwebservice(job, omdb_api_key, title, "")
            logging.debug("response: " + str(response))

        if response == "fail":
            # see if there is a hyphen and split it
            # if title.find("-") > -1:
            while response == "fail" and title.find("-") > 0:
                # dvd_title_slice = title[:title.find("-")]
                title = title.rsplit('-', 1)[0]
                # dvd_title_slice = cleanupstring(dvd_title_slice)
                logging.debug("Trying title: " + title)
                response = callwebservice(job, omdb_api_key, title, year)
                logging.debug("response: " + str(response))

            # if still fail, then try slicing off the last word in a loop
            while response == "fail" and title.count('+') > 0:
                title = title.rsplit('+', 1)[0]
                logging.debug("Trying title: " + title)
                response = callwebservice(job, omdb_api_key, title, year)
                logging.debug("response: " + str(response))
                # Added from pull 366 but we already try without the year.
                # Possible bad/increased rate of false positives
                if response == "fail":
                    logging.debug("Removing year...")
                    response = callwebservice(job, omdb_api_key, title, "")

    # If after everything we dont have a nice title. lets make sure we revert to using job.label
    if not job.hasnicetitle:
        job.title = job.label
        db.session.commit()


def callwebservice(job, omdb_api_key, dvd_title, year=""):
    """ Queries OMDbapi.org for title information and parses type, imdb, and poster info
    """
    if job.config.VIDEOTYPE == "auto":
        strurl = "http://www.omdbapi.com/?t={1}&y={2}&plot=short&r=json&apikey={0}".format(omdb_api_key, dvd_title,
                                                                                           year)
        logging.debug(
            "http://www.omdbapi.com/?t={1}&y={2}&plot=short&r=json&apikey={0}".format("key_hidden", dvd_title, year))
    else:
        strurl = "http://www.omdbapi.com/?t={1}&y={2}&" \
                 "type={3}&plot=short&r=json&apikey={0}".format(omdb_api_key, dvd_title, year, job.config.VIDEOTYPE)
        logging.debug(
            "http://www.omdbapi.com/?t={1}&y={2}&type={3}&plot=short&r=json&apikey={0}".format("key_hidden", dvd_title,
                                                                                               year,
                                                                                               job.config.VIDEOTYPE))

    logging.debug("***Calling webservice with Title: " + str(dvd_title) + " and Year: " + str(year))
    try:
        # strurl = "http://www.omdbapi.com/?t={1}&y={2}&plot=short&
        # r=json&apikey={0}".format(omdb_api_key, dvd_title, year)
        #
        # logging.debug("http://www.omdbapi.com/?t={1}&y={2}&plot=short&
        # r=json&apikey={0}".format("key_hidden", dvd_title, year))
        dvd_title_info_json = urllib.request.urlopen(strurl).read()
    except Exception:
        logging.debug("Webservice failed")
        return "fail"
    else:
        doc = json.loads(dvd_title_info_json.decode())
        if doc['Response'] == "False":
            logging.debug("Webservice failed with error: " + doc['Error'])
            return "fail"
        else:
            # global new_year
            new_year = doc['Year']
            # new_year = job.year_auto = job.year = str(doc['Year'])
            title = clean_for_filename(doc['Title'])
            logging.debug("Webservice successful.  New title is " + title + ".  New Year is: " + new_year)
            job.year_auto = str(new_year)
            job.year = str(new_year)
            job.title_auto = title
            job.title = title
            job.video_type_auto = doc['Type']
            job.video_type = doc['Type']
            job.imdb_id_auto = doc['imdbID']
            job.imdb_id = doc['imdbID']
            job.poster_url_auto = doc['Poster']
            job.poster_url = doc['Poster']
            job.hasnicetitle = True
            utils.database_updater(db, job)
            # db.session.commit()
            return doc['Response']
