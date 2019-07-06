# Identification of dvd/bluray

import os
import sys # noqa # pylint: disable=unused-import
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
# from arm.config.config import cfg

# flake8: noqa: W605


def identify(job, logfile):
    """Identify disc attributes"""

    logging.debug("Identification starting: " + str(job))

    logging.info("Mounting disc to: " + str(job.mountpoint))

    if not os.path.exists(str(job.mountpoint)):
        os.makedirs(str(job.mountpoint))

    os.system("mount " + job.devpath)

    # Check to make sure it's not a data disc
    if job.disctype == "music":
        logging.debug("Disc is music.  Skipping identification")
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

            if res and not job.year == "0000":
                get_video_details(job)
            else:
                job.hasnicetitle = False
                db.session.commit()

            logging.info("Disc title: " + str(job.title) + " : " + str(job.year) + " : " + str(job.video_type))
            logging.debug("Identification complete: " + str(job))

    os.system("umount " + job.devpath)


def clean_for_filename(string):
    """ Cleans up string for use in filename """
    string = re.sub('\[(.*?)\]', '', string)
    string = re.sub('\s+', ' ', string)
    string = string.replace(' : ', ' - ')
    string = string.replace(':', '-')
    string = string.strip()
    return re.sub('[^\w\-_\.\(\) ]', '', string)


def identify_dvd(job):
    """ Calculates CRC64 for the DVD and calls Windows Media
        Metaservices and returns the Title and year of DVD """
    logging.debug(str(job))

    try:
        crc64 = pydvdid.compute(str(job.mountpoint))
    except pydvdid.exceptions.PydvdidException as e:
        logging.error("Pydvdid failed with the error: " + str(e))
        return False

    logging.info("DVD CRC64 hash is: " + str(crc64))
    job.crc_id = str(crc64)
    urlstring = "http://metaservices.windowsmedia.com/pas_dvd_B/template/GetMDRDVDByCRC.xml?CRC={0}".format(str(crc64))
    logging.debug(urlstring)

    try:
        dvd_info_xml = urllib.request.urlopen(
            "http://metaservices.windowsmedia.com/pas_dvd_B/template/GetMDRDVDByCRC.xml?CRC={0}".
            format(crc64)).read()
    except OSError as e:
        dvd_info_xml = False
        dvd_title = "not_identified"
        dvd_release_date = "0000"
        logging.error("Failed to reach windowsmedia web service.  Error number is: " + str(e.errno))
        # return False

    try:
        if not dvd_info_xml:
            pass
        else:
            doc = xmltodict.parse(dvd_info_xml)
            dvd_title = doc['METADATA']['MDR-DVD']['dvdTitle']
            dvd_release_date = doc['METADATA']['MDR-DVD']['releaseDate']
            dvd_title = dvd_title.strip()
            dvd_title = clean_for_filename(dvd_title)
            if dvd_release_date is not None:
                dvd_release_date = dvd_release_date.split()[0]
            else:
                dvd_release_date = ""
    except KeyError:
        dvd_title = "not_identified"
        dvd_release_date = "0000"
        logging.error("Windows Media request returned no result.  Likely the DVD is not in their database.")
        # return False

    job.title = job.title_auto = dvd_title
    job.year = job.year_auto = dvd_release_date
    db.session.commit()

    return True


def identify_bluray(job):
    """ Get's Blu-Ray title by parsing XML in bdmt_eng.xml """

    try:
        with open(job.mountpoint + '/BDMV/META/DL/bdmt_eng.xml', "rb") as xml_file:
            doc = xmltodict.parse(xml_file.read())
    except OSError as e:
        logging.error("Disc is a bluray, but bdmt_eng.xml could not be found.  Disc cannot be identified.  Error number is: " + str(e.errno))
        return False

    try:
        bluray_title = doc['disclib']['di:discinfo']['di:title']['di:name']
    except KeyError:
        bluray_title = "not_identified"
        bluray_year = "0000"
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


def get_video_details(job):
    """ Clean up title and year.  Get video_type, imdb_id, poster_url from
    omdbapi.com webservice.\n

    job = Instance of Job class\n
    """

    title = job.title
    year = job.year
    if year is None:
        year = ""

    # needs_new_year = False
    omdb_api_key = job.config.OMDB_API_KEY

    logging.debug("Title: " + title + " | Year: " + year)

    # dvd_title_clean = cleanupstring(dvd_title)
    title = title.strip()
    title = re.sub('[_ ]', "+", title)

    logging.debug("Calling webservice with title: " + title + " and year: " + year)
    response = callwebservice(job, omdb_api_key, title, year)
    logging.debug("response: " + response)

    # handle failures
    # this is a little kludgy, but it kind of works...
    if (response == "fail"):

        # first try subtracting one year.  This accounts for when
        # the dvd release date is the year following the movie release date
        logging.debug("Subtracting 1 year...")
        response = callwebservice(job, omdb_api_key, title, str(int(year) - 1))
        logging.debug("response: " + response)

        # try submitting without the year
        if response == "fail":
            # year needs to be changed
            logging.debug("Removing year...")
            response = callwebservice(job, omdb_api_key, title, "")
            logging.debug("response: " + response)

        # if response != "fail":
        #     # that means the year is wrong.
        #     needs_new_year = True
        #     logging.debug("Setting needs_new_year = True.")

        if response == "fail":
            # see if there is a hyphen and split it
            # if title.find("-") > -1:
            while response == "fail" and title.find("-") > 0:
                # dvd_title_slice = title[:title.find("-")]
                title = title.rsplit('-', 1)[0]
                # dvd_title_slice = cleanupstring(dvd_title_slice)
                logging.debug("Trying title: " + title)
                response = callwebservice(job, omdb_api_key, title, year)
                logging.debug("response: " + response)

            # if still fail, then try slicing off the last word in a loop
            while response == "fail" and title.count('+') > 0:
                title = title.rsplit('+', 1)[0]
                logging.debug("Trying title: " + title)
                response = callwebservice(job, omdb_api_key, title, year)
                logging.debug("response: " + response)


def callwebservice(job, omdb_api_key, dvd_title, year=""):
    """ Queries OMDbapi.org for title information and parses type, imdb, and poster info
    """

    if job.config.VIDEOTYPE == "auto":
        strurl = "http://www.omdbapi.com/?t={1}&y={2}&plot=short&r=json&apikey={0}".format(omdb_api_key, dvd_title, year)
        logging.debug("http://www.omdbapi.com/?t={1}&y={2}&plot=short&r=json&apikey={0}".format("key_hidden", dvd_title, year))
    else:
        strurl = "http://www.omdbapi.com/?t={1}&y={2}&type={3}&plot=short&r=json&apikey={0}".format(omdb_api_key, dvd_title, year, job.config.VIDEOTYPE)
        logging.debug("http://www.omdbapi.com/?t={1}&y={2}&type={3}&plot=short&r=json&apikey={0}".format("key_hidden", dvd_title, year, job.config.VIDEOTYPE))

    logging.debug("***Calling webservice with Title: " + dvd_title + " and Year: " + year)
    try:
        # strurl = "http://www.omdbapi.com/?t={1}&y={2}&plot=short&r=json&apikey={0}".format(omdb_api_key, dvd_title, year)
        # logging.debug("http://www.omdbapi.com/?t={1}&y={2}&plot=short&r=json&apikey={0}".format("key_hidden", dvd_title, year))
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
            db.session.commit()
            return doc['Response']
