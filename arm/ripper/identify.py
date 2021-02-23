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


# from arm.config.config import cfg

# flake8: noqa: W605


def identify(job, logfile):
    """Identify disc attributes"""
    # Safe way of dealing with log files if the users need to post it online
    # cleanlog = makecleanlogfile(job)
    # logging.debug("#### --- job ----"+ str(cleanlog))

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
            # Need to check if year is "0000"  or ""
            if res and not job.year == "0000":
                get_video_details(job)
            else:
                job.hasnicetitle = False
                db.session.commit()

            logging.info("Disc title: " + str(job.title) + " : " + str(job.year) + " : " + str(job.video_type))
            # Safe way of dealing with log files if the users need to post it online
            cleanlog = makecleanlogfile(job)
            logging.debug("#### --- job ----" + str(cleanlog))

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
        logging.error(
            "Disc is a bluray, but bdmt_eng.xml could not be found.  Disc cannot be identified.  Error number is: "
            + str(e.errno))
        return False

    try:
        bluray_title = doc['disclib']['di:discinfo']['di:title']['di:name']
    except KeyError:
        # Changed from pull 366
        bluray_title = str(fallback_title)
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
    """ Calculates CRC64 for the DVD and calls Windows Media
        Metaservices and returns the Title and year of DVD """
    # Added from pull 366
    """ Manipulates the DVD title and calls OMDB to try and 	
    lookup the title """

    # Safe way of dealing with log files if the users need to post it online
    # cleanlog = makecleanlogfile(job)
    # logging.debug("#### --- job ----" + str(cleanlog))

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
    except pydvdid.exceptions.PydvdidException as e:
        logging.error("Pydvdid failed with the error: " + str(e))
        dvd_title = fallback_title = str(job.label)

    logging.info("DVD CRC64 hash is: " + str(crc64))
    job.crc_id = str(crc64)

    # Dead needs removing
    urlstring = "http://metaservices.windowsmedia.com/pas_dvd_B/template/GetMDRDVDByCRC.xml?CRC={0}".format(str(crc64))
    logging.debug(urlstring)

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
    # Set out title from the job
    # return if not identified
    title = job.title
    if title == "not identified":
        return

    # strip all non-numeric chars and use that for year
    # TODO: possible need for making sure year is a str
    year = re.sub("[^0-9]", "", job.year)
    if year is None:
        year = ""

    # needs_new_year = False
    omdb_api_key = job.config.OMDB_API_KEY

    # TODO: possible need for making sure str
    # TODO: possible need for making sure str
    logging.debug("Title: " + title + " | Year: " + year)

    # dvd_title_clean = cleanupstring(dvd_title)
    title = title.strip()
    title = re.sub('[_ ]', "+", title)

    # TODO: possible need for making sure is a str
    logging.debug("Calling webservice with title: " + title + " and year: " + year)
    response = callwebservice(job, omdb_api_key, title, year)
    logging.debug("response: " + response)

    # handle failures
    # this is a little kludgy, but it kind of works...
    if (response == "fail"):

        if year:
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
                # Added from pull 366 but we already try without the year.
                # Possible bad/increased rate of false positives
                if response == "fail":
                    logging.debug("Removing year...")
                    response = callwebservice(job, omdb_api_key, title, "")


def callwebservice(job, omdb_api_key, dvd_title, year=""):
    """ Queries OMDbapi.org for title information and parses type, imdb, and poster info
    """

    if job.config.VIDEOTYPE == "auto":
        strurl = "http://www.omdbapi.com/?t={1}&y={2}&plot=short&r=json&apikey={0}".format(omdb_api_key, dvd_title,
                                                                                           year)
        logging.debug(
            "http://www.omdbapi.com/?t={1}&y={2}&plot=short&r=json&apikey={0}".format("key_hidden", dvd_title, year))
    else:
        strurl = "http://www.omdbapi.com/?t={1}&y={2}&type={3}&plot=short&r=json&apikey={0}".format(omdb_api_key,
                                                                                                    dvd_title, year,
                                                                                                    job.config.VIDEOTYPE)
        logging.debug(
            "http://www.omdbapi.com/?t={1}&y={2}&type={3}&plot=short&r=json&apikey={0}".format("key_hidden", dvd_title,
                                                                                               year,
                                                                                               job.config.VIDEOTYPE))

    logging.debug("***Calling webservice with Title: " + dvd_title + " and Year: " + year)
    try:
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


def makecleanlogfile(logfile):
    """
    Clean the log of secret keys and return the removed string
    arguments:
    logfile - the log as string
    returns - a clean string with all keys and api secrets removed
    """
    # TODO: make this cleaner/smaller
    # lets make sure we are using a string
    logfile = str(logfile)
    # logging.debug("inside makecleanlogfile: " + str(logfile) + "\n\r")
    out = re.sub("\(PB_KEY=.*?\)", '(PB_KEY=** REMOVED **)', logfile)  # noqa W605
    out = re.sub("\(EMBY_PASSWORD=.*?\)", '(EMBY_PASSWORD=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(EMBY_API_KEY=.*?\)", '(EMBY_API_KEY=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(EMBY_SERVER=.*?\)", '(EMBY_SERVER=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(IFTTT_KEY=.*?\)", '(IFTTT_KEY=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(OMDB_API_KEY=.*?\)", '(OMDB_API_KEY=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(PO_APP_KEY=.*?\)", '(PO_APP_KEY=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(PO_USER_KEY=.*?\)", '(PO_USER_KEY=** REMOVED **)', out)  # noqa W605
    # \(WEBSERVER_IP=(.*?)\.3[0-9]{1,3}\.[0-9]{1,3}\)
    ips = re.search('\(WEBSERVER_IP=(.*?)\.[0-9]{1,3}\.[0-9]{1,3}\)', out)  # noqa W605
    if ips:
        ip = ips.group(1)
        out = re.sub("\(WEBSERVER_IP=.*?\)", '(WEBSERVER_IP=' + str(ip) + '.xx.xx)', out)  # noqa W605

    # Apprise notifications
    out = re.sub("\(DISCORD_WEBHOOK_ID=.*?\)", '(DISCORD_WEBHOOK_ID=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(DISCORD_TOKEN=.*?\)", '(DISCORD_TOKEN=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(FAAST_TOKEN=.*?\)", '(FAAST_TOKEN=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(FLOCK_TOKEN=.*?\)", '(FLOCK_TOKEN=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(GITTER_TOKEN=.*?\)", '(GITTER_TOKEN=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(GOTIFY_HOST=.*?\)", '(GOTIFY_HOST=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(GROWL_HOST=.*?\)", '(GROWL_HOST=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(GROWL_PASS=.*?\)", '(GROWL_PASS=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(JOIN_API=.*?\)", '(JOIN_API=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(JOIN_DEVICE=.*?\)", '(JOIN_DEVICE=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(KODI_HOST=.*?\)", '(KODI_HOST=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(KODI_PASS=.*?\)", '(KODI_PASS=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(KUMULOS_API=.*?\)", '(KUMULOS_API=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(LAMETRIC_API=.*?\)", '(LAMETRIC_API=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(LAMETRIC_HOST=.*?\)", '(LAMETRIC_HOST=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(LAMETRIC_APP_ID=.*?\)", '(LAMETRIC_APP_ID=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(LAMETRIC_TOKEN=.*?\)", '(LAMETRIC_TOKEN=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(MAILGUN_DOMAIN=.*?\)", '(MAILGUN_DOMAIN=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(MAILGUN_APIKEY=.*?\)", '(MAILGUN_APIKEY=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(MATRIX_HOST=.*?\)", '(MATRIX_HOST=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(MATRIX_PASS=.*?\)", '(MATRIX_PASS=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(MATRIX_TOKEN=.*?\)", '(MATRIX_TOKEN=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(MSTEAMS_TOKENA=.*?\)", '(MSTEAMS_TOKENA=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(MSTEAMS_TOKENB=.*?\)", '(MSTEAMS_TOKENB=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(MSTEAMS_TOKENC=.*?\)", '(MSTEAMS_TOKENC=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(NEXTCLOUD_HOST=.*?\)", '(NEXTCLOUD_HOST=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(NEXTCLOUD_ADMINPASS=.*?\)", '(NEXTCLOUD_ADMINPASS=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(NOTICA_TOKEN=.*?\)", '(NOTICA_TOKEN=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(NOTIFICO_PROJECTID=.*?\)", '(NOTIFICO_PROJECTID=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(NOTIFICO_MESSAGEHOOK=.*?\)", '(NOTIFICO_MESSAGEHOOK=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(OFFICE365_TENANTID=.*?\)", '(OFFICE365_TENANTID=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(OFFICE365_CLIENT_ID=.*?\)", '(OFFICE365_CLIENT_ID=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(OFFICE365_CLIENT_SECRET=.*?\)", '(OFFICE365_CLIENT_SECRET=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(POPCORN_API=.*?\)", '(POPCORN_API=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(POPCORN_EMAIL=.*?\)", '(POPCORN_EMAIL=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(POPCORN_PHONENO=.*?\)", '(POPCORN_PHONENO=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(PROWL_API=.*?\)", '(PROWL_API=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(PROWL_PROVIDERKEY=.*?\)", '(PROWL_PROVIDERKEY=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(PUSH_API=.*?\)", '(PUSH_API=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(PUSHED_APP_KEY=.*?\)", '(PUSHED_APP_KEY=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(PUSHED_APP_SECRET=.*?\)", '(PUSHED_APP_SECRET=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(PUSHSAFER_KEY=.*?\)", '(PUSHSAFER_KEY=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(ROCKETCHAT_HOST=.*?\)", '(ROCKETCHAT_HOST=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(ROCKETCHAT_PASS=.*?\)", '(ROCKETCHAT_PASS=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(ROCKETCHAT_WEBHOOK=.*?\)", '(ROCKETCHAT_WEBHOOK=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(RYVER_ORG=.*?\)", '(RYVER_ORG=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(RYVER_TOKEN=.*?\)", '(RYVER_TOKEN=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(SENDGRID_API=.*?\)", '(SENDGRID_API=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(SENDGRID_FROMMAIL=.*?\)", '(SENDGRID_FROMMAIL=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(SIMPLEPUSH_API=.*?\)", '(SIMPLEPUSH_API=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(SLACK_TOKENA=.*?\)", '(SLACK_TOKENA=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(SLACK_TOKENB=.*?\)", '(SLACK_TOKENB=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(SLACK_TOKENC=.*?\)", '(SLACK_TOKENC=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(SPARKPOST_API=.*?\)", '(SPARKPOST_API=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(SPARKPOST_HOST=.*?\)", '(SPARKPOST_HOST=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(SPONTIT_API=.*?\)", '(SPONTIT_API=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(SPONTIT_USER_ID=.*?\)", '(SPONTIT_USER_ID=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(TELEGRAM_BOT_TOKEN=.*?\)", '(TELEGRAM_BOT_TOKEN=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(TELEGRAM_CHAT_ID=.*?\)", '(TELEGRAM_CHAT_ID=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(TWIST_EMAIL=.*?\)", '(TWIST_EMAIL=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(TWIST_PASS=.*?\)", '(TWIST_PASS=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(XBMC_HOST=.*?\)", '(XBMC_HOST=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(XBMC_PASS=.*?\)", '(XBMC_PASS=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(XMPP_HOST=.*?\)", '(XMPP_HOST=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(XMPP_PASS=.*?\)", '(XMPP_PASS=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(WEBEX_TEAMS_TOKEN=.*?\)", '(WEBEX_TEAMS_TOKEN=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(ZILUP_CHAT_TOKEN=.*?\)", '(ZILUP_CHAT_TOKEN=** REMOVED **)', out)  # noqa W605
    out = re.sub("\(ZILUP_CHAT_ORG=.*?\)", '(ZILUP_CHAT_ORG=** REMOVED **)', out)  # noqa W605
    # format for more entries
    # out = re.sub("\(CONFIG_ID=.*?\)", '(CONFIG_ID=** REMOVED **)', out)

    # logging.debug("our clean log string" + str(out))
    return out
