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
import requests

from arm.ripper import music_brainz
from arm.ripper import utils
from arm.ui import db
from arm.config.config import cfg


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
        job.label = music_brainz.main(job)
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

        if cfg["GET_VIDEO_TITLE"]:
            # get crc_id (dvd only), title, year
            if job.disctype == "dvd":
                res = identify_dvd(job)
            if job.disctype == "bluray":
                res = identify_bluray(job)
            # Need to check if year is "0000"  or ""
            if res and job.year != "0000":
                if cfg['METADATA_PROVIDER'].lower() == "tmdb":
                    tmdb_get_media_type(job)
                elif cfg['METADATA_PROVIDER'].lower() == "omdb":
                    get_video_details(job)
                else:
                    logging.debug("unknown provider")
            else:
                job.hasnicetitle = False
                db.session.commit()

            logging.info(
                "Disc title Post ident: " + str(job.title) + " : " + str(job.year) + " : " + str(job.video_type))
            logging.debug("identify.job.end ---- \n\r" + job.pretty_table())

    os.system("umount " + job.devpath)


def clean_for_filename(string):
    """ Cleans up string for use in filename """
    string = re.sub('\\[(.*?)\\]', '', string)
    string = re.sub('\\s+', ' ', string)
    string = string.replace(' : ', ' - ')
    string = string.replace(':', '-')
    # Added from pull 366
    string = string.replace('&', 'and')
    string = string.replace("\\", " - ")
    string = string.strip()

    # Added from pull 366
    # testing why the return function isn't cleaning
    # [^\w_.() -]  # New without errors
    # [^\w\-_\.\(\)]  #  Gives warning of extra escapes
    return re.sub('[^\\w_.() -]', '', string)
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
        # Maybe call OMdb with label when we cant find any ident on disc ?
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
    try:
        crc64 = pydvdid.compute(str(job.mountpoint))
        fallback_title = f"{job.label}_{crc64}"
        dvd_title = fallback_title
        logging.info("DVD CRC64 hash is: " + str(crc64))
        job.crc_id = str(crc64)
        urlstring = f"http://1337server.pythonanywhere.com/api/v1/?mode=s&crc64={crc64}"
        logging.debug(urlstring)
        dvd_info_xml = urllib.request.urlopen(urlstring).read()
        x = json.loads(dvd_info_xml)
        logging.debug("dvd xml - " + str(x))
        logging.debug(f"results = {x['results']}")
        if bool(x['success']):
            job.title = x['results']['0']['title']
            job.year = x['results']['0']['year']
            job.imdb_id = x['results']['0']['imdb_id']
            job.video_type = x['results']['0']['video_type']
            db.session.commit()
            return True
    except pydvdid.exceptions.PydvdidException as e:
        logging.error("Pydvdid failed with the error: " + str(e))
        dvd_title = fallback_title = str(job.label)
    # TODO: make use of dvd_info_xml again if found

    logging.debug("dvd_title_label= " + str(dvd_title))
    # strip all non-numeric chars and use that for year
    year = re.sub(r"[^0-9]", "", str(job.year))
    # next line is not really needed, but we dont want to leave an x somewhere
    dvd_title = job.label.replace("16x9", "")
    # Rip out any not alpha chars replace with
    dvd_title = re.sub(r"[^a-zA-Z ]", " ", dvd_title)
    logging.debug("dvd_title ^a-z= " + str(dvd_title))
    # rip out any SKU's at the end of the line
    dvd_title = re.sub(r"SKU\b", "", dvd_title)
    logging.debug("dvd_title SKU$= " + str(dvd_title))

    # try to contact omdb/tmdb
    if cfg['METADATA_PROVIDER'].lower() == "tmdb":
        logging.debug("using tmdb")
        tmdb_api_key = cfg['TMDB_API_KEY']
        dvd_info_xml = call_tmdb_service(job, tmdb_api_key, dvd_title, year)
    elif cfg['METADATA_PROVIDER'].lower() == "omdb":
        logging.debug("using omdb")
        dvd_info_xml = callwebservice(job, cfg["OMDB_API_KEY"], dvd_title, year)
    else:
        raise Exception("Error with metadata provider - Not supported")
    logging.debug("DVD_INFO_XML: " + str(dvd_info_xml))
    # Not sure this is needed anymore because of CWS()
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

    omdb_api_key = cfg["OMDB_API_KEY"]
    tmdb_api_key = cfg['TMDB_API_KEY']
    if cfg['METADATA_PROVIDER'].lower() == "tmdb":
        def call_web_service(j, api_key, dvd_title, y, tmdb_api=tmdb_api_key):
            return tmdb_get_media_type(j)
    elif cfg['METADATA_PROVIDER'].lower() == "omdb":
        def call_web_service(j, api_key, dvd_title, y):
            return callwebservice(j, api_key, dvd_title, y)
    else:
        return None
    logging.debug("Title: " + title + " | Year: " + year)
    logging.debug("Calling webservice with title: " + title + " and year: " + year)

    response = call_web_service(job, omdb_api_key, title, year)
    # logging.debug("response: " + str(response))

    # handle failures
    # this is a little kludgy, but it kind of works...
    if response == "fail":
        if year:
            # first try subtracting one year.  This accounts for when
            # the dvd release date is the year following the movie release date
            logging.debug("Subtracting 1 year...")
            response = call_web_service(job, omdb_api_key, title, str(int(year) - 1))
            logging.debug("response: " + str(response))

        # try submitting without the year
        if response == "fail":
            # year needs to be changed
            logging.debug("Removing year...")
            response = call_web_service(job, omdb_api_key, title, "")
            logging.debug("response: " + str(response))

        if response == "fail":
            # see if there is a hyphen and split it
            # if title.find("-") > -1:
            while response == "fail" and title.find("-") > 0:
                # dvd_title_slice = title[:title.find("-")]
                title = title.rsplit('-', 1)[0]
                # dvd_title_slice = cleanupstring(dvd_title_slice)
                logging.debug("Trying title: " + title)
                response = call_web_service(job, omdb_api_key, title, year)
                logging.debug("response: " + str(response))

            # if still fail, then try slicing off the last word in a loop
            while response == "fail" and title.count('+') > 0:
                title = title.rsplit('+', 1)[0]
                logging.debug("Trying title: " + title)
                response = call_web_service(job, omdb_api_key, title, year)
                logging.debug("response: " + str(response))
                # Added from pull 366 but we already try without the year.
                # Possible bad/increased rate of false positives
                if response == "fail":
                    logging.debug("Removing year...")
                    response = call_web_service(job, omdb_api_key, title, "")

    # If after everything we dont have a nice title. lets make sure we revert to using job.label
    if not job.hasnicetitle:
        job.title = job.label
        db.session.commit()


def callwebservice(job, omdb_api_key, dvd_title, year=""):
    """ Queries OMDbapi.org for title information and parses type, imdb, and poster info
    """
    if cfg["VIDEOTYPE"] == "auto":
        strurl = f"http://www.omdbapi.com/?t={dvd_title}&y={year}&plot=short&r=json&apikey={omdb_api_key}"
        logging.debug(f"http://www.omdbapi.com/?t={dvd_title}&y={year}&plot=short&r=json&apikey=key_hidden")
    else:
        strurl = f"http://www.omdbapi.com/?t={dvd_title}&y={year}&type={cfg['VIDEOTYPE']}" \
                 f"&plot=short&r=json&apikey={omdb_api_key}"
        logging.debug(
            f"http://www.omdbapi.com/?t={dvd_title}&y={year}&type={cfg['VIDEOTYPE']}"
            f"&plot=short&r=json&apikey=key_hidden")

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
            args = {
                'year_auto': str(new_year),
                'year': str(new_year),
                'title_auto': title,
                'title': title,
                'video_type_auto': doc['Type'],
                'video_type': doc['Type'],
                'imdb_id_auto': doc['imdbID'],
                'imdb_id': doc['imdbID'],
                'poster_url_auto': doc['Poster'],
                'poster_url': doc['Poster'],
                'hasnicetitle': True
            }
            utils.database_updater(args, job)
            # db.session.commit()
            return doc['Response']


def call_tmdb_service(job, tmdb_api_key, dvd_title, year=""):
    """
        Queries api.themoviedb.org for movies close to the query

    """
    # Movies and TV shows
    # https://api.themoviedb.org/3/search/multi?api_key=<<api_key>>&query=aa
    # Movie with tons of extra details
    # https://api.themoviedb.org/3/movie/78?api_key=
    # &append_to_response=alternative_titles,changes,credits,images,keywords,lists,releases,reviews,similar,videos
    if year:
        url = f"https://api.themoviedb.org/3/search/movie?api_key={tmdb_api_key}&query={dvd_title}&year={year}"
        clean_url = f"https://api.themoviedb.org/3/search/movie?api_key=hidden&query={dvd_title}&year={year}"
    else:
        url = f"https://api.themoviedb.org/3/search/movie?api_key={tmdb_api_key}&query={dvd_title}"
        clean_url = f"https://api.themoviedb.org/3/search/movie?api_key=hidden&query={dvd_title}"
    poster_size = "original"
    poster_base = f"http://image.tmdb.org/t/p/{poster_size}"
    # Making a get request
    logging.debug(f"url = {clean_url}")
    response = requests.get(url)
    p = json.loads(response.text)
    logging.debug(p)
    x = {}
    # Check for movies
    if 'total_results' in p and p['total_results'] > 0:
        logging.debug(p['total_results'])
        for s in p['results']:
            s['poster_path'] = s['poster_path'] if s['poster_path'] is not None else None
            s['release_date'] = '0000-00-00' if 'release_date' not in s else s['release_date']
            s['imdbID'] = tmdb_get_imdb(s['id'], tmdb_api_key)
            s['Year'] = re.sub("-[0-9]{0,2}-[0-9]{0,2}", "", s['release_date'])
            s['Title'] = s['title']
            s['Type'] = "movie"
            logging.debug(f"{s['title']} ({s['Year']})- {poster_base}{s['poster_path']}")
            s['Poster'] = f"{poster_base}{s['poster_path']}"  # print(poster_url)
            s['background_url'] = f"{poster_base}{s['backdrop_path']}"
            logging.debug(s['background_url'])
            dvd_title_pretty = re.sub(r"\+", " ", dvd_title)
            logging.debug(f"trying {dvd_title.capitalize()} == {s['title'].capitalize()}")
            if dvd_title_pretty.capitalize() == s['title'].capitalize():
                s['Search'] = s
                logging.debug("x=" + str(x))
                s['Response'] = True
                # global new_year
                new_year = s['Year']
                # new_year = job.year_auto = job.year = str(x['Year'])
                title = clean_for_filename(s['Title'])
                logging.debug("Webservice successful.  New title is " + title + ".  New Year is: " + new_year)
                args = {
                    'year_auto': str(new_year),
                    'year': str(new_year),
                    'title_auto': title,
                    'title': title,
                    'video_type_auto': s['Type'],
                    'video_type': s['Type'],
                    'imdb_id_auto': s['imdbID'],
                    'imdb_id': s['imdbID'],
                    'poster_url_auto': s['Poster'],
                    'poster_url': s['Poster'],
                    'hasnicetitle': True
                }
                utils.database_updater(args, job)
                return s
        x['Search'] = p['results']
        return x
    else:
        # Movies have failed check for tv series
        url = f"https://api.themoviedb.org/3/search/tv?api_key={tmdb_api_key}&query={dvd_title}"
        response = requests.get(url)
        p = json.loads(response.text)
        # v = json.dumps(response.json(), indent=4, sort_keys=True)
        logging.debug(p)
        x = {}
        if 'total_results' in p and p['total_results'] > 0:
            logging.debug(p['total_results'])
            for s in p['results']:
                logging.debug(s)
                s['poster_path'] = s['poster_path'] if s['poster_path'] is not None else None
                s['release_date'] = '0000-00-00' if 'release_date' not in s else s['release_date']
                s['imdbID'] = tmdb_get_imdb(s['id'], tmdb_api_key)
                reg = "-[0-9]{0,2}-[0-9]{0,2}"
                s['Year'] = re.sub(reg, "", s['first_air_date']) if 'first_air_date' in s else \
                    re.sub(reg, "", s['release_date'])
                s['Title'] = s['title'] if 'title' in s else s['name']  # This isnt great
                s['Type'] = "series"
                logging.debug(f"{s['Title']} ({s['Year']})- {poster_base}{s['poster_path']}")
                s['Poster'] = f"{poster_base}{s['poster_path']}"  # print(poster_url)
                s['background_url'] = f"{poster_base}{s['backdrop_path']}"
                logging.debug(s['background_url'])
                dvd_title_pretty = re.sub(r"\+", " ", dvd_title)
                logging.debug(f"trying {dvd_title.capitalize()} == {s['Title'].capitalize()}")
                if dvd_title_pretty.capitalize() == s['Title'].capitalize():
                    s['Search'] = s
                    logging.debug("x=" + str(x))
                    s['Response'] = True
                    # global new_year
                    new_year = s['Year']
                    # new_year = job.year_auto = job.year = str(x['Year'])
                    title = clean_for_filename(s['Title'])
                    logging.debug("Webservice successful.  New title is " + title + ".  New Year is: " + new_year)
                    args = {
                        'year_auto': str(new_year),
                        'year': str(new_year),
                        'title_auto': title,
                        'title': title,
                        'video_type_auto': s['Type'],
                        'video_type': s['Type'],
                        'imdb_id_auto': s['imdbID'],
                        'imdb_id': s['imdbID'],
                        'poster_url_auto': s['Poster'],
                        'poster_url': s['Poster'],
                        'hasnicetitle': True
                    }
                    utils.database_updater(args, job)
                    return s
            x['Search'] = p['results']
            return x
        logging.debug("no results found")
        return "fail"


def tmdb_get_media_type(job):
    """ Clean up title and year.  Get video_type, imdb_id, poster_url from
    tmdb API.\n

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

    tmdb_api_key = cfg['TMDB_API_KEY']

    logging.debug("Title: " + title + " | Year: " + year)
    logging.debug("Calling webservice with title: " + title + " and year: " + year)
    response = call_tmdb_service(job, tmdb_api_key, title, year)
    # logging.debug("response: " + str(response))

    # handle failures
    # this is a little kludgy, but it kind of works...
    if response == "fail":
        if year:
            # first try subtracting one year.  This accounts for when
            # the dvd release date is the year following the movie release date
            logging.debug("Subtracting 1 year...")
            response = call_tmdb_service(job, tmdb_api_key, title, str(int(year) - 1))
            logging.debug("response: " + str(response))

        # try submitting without the year
        if response == "fail":
            # year needs to be changed
            logging.debug("Removing year...")
            response = call_tmdb_service(job, tmdb_api_key, title, "")
            logging.debug("response: " + str(response))

        if response == "fail":
            # see if there is a hyphen and split it
            # if title.find("-") > -1:
            while response == "fail" and title.find("-") > 0:
                # dvd_title_slice = title[:title.find("-")]
                title = title.rsplit('-', 1)[0]
                # dvd_title_slice = cleanupstring(dvd_title_slice)
                logging.debug("Trying title: " + title)
                response = call_tmdb_service(job, tmdb_api_key, title, year)
                logging.debug("response: " + str(response))

            # if still fail, then try slicing off the last word in a loop
            while response == "fail" and title.count('+') > 0:
                title = title.rsplit('+', 1)[0]
                logging.debug("Trying title: " + title)
                response = call_tmdb_service(job, tmdb_api_key, title, year)
                logging.debug("response: " + str(response))
                # Added from pull 366 but we already try without the year.
                # Possible bad/increased rate of false positives
                if response == "fail":
                    logging.debug("Removing year...")
                    response = call_tmdb_service(job, tmdb_api_key, title, "")

    # If after everything we dont have a nice title. lets make sure we revert to using job.label
    if not job.hasnicetitle:
        job.title = job.label
        db.session.commit()


def tmdb_get_imdb(tmdb_id, tmdb_api_key):
    """
        Queries api.themoviedb.org for imdb_id by TMDB id

    """
    url = f"https://api.themoviedb.org/3/movie/{tmdb_id}?api_key={tmdb_api_key}&" \
          f"append_to_response=alternative_titles,credits,images,keywords,releases,reviews,similar,videos,external_ids"
    clean_url = f"https://api.themoviedb.org/3/movie/{tmdb_id}?api_key=hidden&" \
          f"append_to_response=images,keywords,releases,videos,external_ids"

    # f"https://api.themoviedb.org/3/tv/1606?api_key={tmdb_api_key}"
    # Making a get request
    logging.debug(clean_url)
    response = requests.get(url)
    p = json.loads(response.text)
    if 'status_code' not in p:
        p['imdbID'] = p['external_ids']['imdb_id']
    else:
        p['imdbID'] = "NA"
    return p['imdbID']
