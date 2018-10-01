#!/usr/bin/python3

import sys # noqa # pylint: disable=unused-import
import argparse
import urllib
import os # noqa # pylint: disable=unused-import
import xmltodict # noqa # pylint: disable=unused-import
import logging
import json
import re

from arm.config.config import cfg


def entry():
    """ Entry to program, parses arguments"""
    parser = argparse.ArgumentParser(description='Get type of dvd--movie or tv series')
    parser.add_argument('-t', '--title', help='Title', required=True)
    # parser.add_argument('-k', '--key', help='API_Key', dest='omdb_api_key', required=True)

    return parser.parse_args()


def getdvdtype(job):
    """ Queries OMDbapi.org for title information and parses if it's a movie
        or a tv series """

    dvd_title = job.title
    year = job.year
    needs_new_year = False
    omdb_api_key = cfg['OMDB_API_KEY']

    logging.debug("Title: " + dvd_title + " | Year: " + year)

    dvd_title_clean = cleanupstring(dvd_title)

    if year is None:
        year = ""

    logging.debug("Calling webservice with title: " + dvd_title_clean + " and year: " + year)
    dvd_type = callwebservice(job, omdb_api_key, dvd_title_clean, year)
    logging.debug("dvd_type: " + dvd_type)

    # handle failures
    # this is a little kludgy, but it kind of works...
    if (dvd_type == "fail"):

        # first try submitting without the year
        logging.debug("Removing year...")
        dvd_type = callwebservice(job, omdb_api_key, dvd_title_clean, "")
        logging.debug("dvd_type: " + dvd_type)

        if dvd_type != "fail":
            # that means the year is wrong.
            needs_new_year = True
            logging.debug("Setting needs_new_year = True.")

        if dvd_type == "fail":
            # second see if there is a hyphen and split it
            if dvd_title.find("-") > -1:
                dvd_title_slice = dvd_title[:dvd_title.find("-")]
                dvd_title_slice = cleanupstring(dvd_title_slice)
                logging.debug("Trying title: " + dvd_title_slice)
                dvd_type = callwebservice(job, omdb_api_key, dvd_title_slice, year)
                logging.debug("dvd_type: " + dvd_type)

            # if still fail, then try slicing off the last word in a loop
            while dvd_type == "fail" and dvd_title_clean.count('+') > 0:
                dvd_title_clean = dvd_title_clean.rsplit('+', 1)[0]
                logging.debug("Trying title: " + dvd_title_clean)
                dvd_type = callwebservice(job, omdb_api_key, dvd_title_clean, year)
                logging.debug("dvd_type: " + dvd_type)

    if needs_new_year:
        #     #pass the new year back to bash to handle
        #     global new_year
        #     return dvd_type + "#" + new_year
        return (dvd_type, new_year)
    else:
        #     return dvd_type
        return (dvd_type, year)


def cleanupstring(string):
    # clean up title string to pass to OMDbapi.org
    string = string.strip()
    return re.sub('[_ ]', "+", string)


def callwebservice(job, omdb_api_key, dvd_title, year=""):
    """ Queries OMDbapi.org for title information and parses if it's a movie
        or a tv series """

    logging.debug("***Calling webservice with Title: " + dvd_title + " and Year: " + year)
    try:
        strurl = "http://www.omdbapi.com/?t={1}&y={2}&plot=short&r=json&apikey={0}".format(omdb_api_key, dvd_title, year)
        logging.debug("http://www.omdbapi.com/?t={1}&y={2}&plot=short&r=json&apikey={0}".format("key_hidden", dvd_title, year))
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
            global new_year
            new_year = doc['Year']
            title = doc['Title']
            logging.debug("Webservice successful.  New title is " + title + ".  New Year is: " + new_year)
            job.year = str(new_year)
            job.title = title
            job.video_type = doc['Type']
            job.imdb_id = doc['imdbID']
            job.poster_url = doc['Poster']
            return doc['Type']


def main(job):

    logging.debug("Entering getvideotype module")
    dvd_type, year = getdvdtype(job)
    return()
