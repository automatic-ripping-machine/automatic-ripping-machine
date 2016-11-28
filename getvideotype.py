#!/usr/bin/python3

import sys
import argparse
import urllib
import os
import xmltodict
import json
import re

def entry():
    """ Entry to program, parses arguments"""
    parser = argparse.ArgumentParser(description='Get type of dvd--movie or tv series')
    parser.add_argument('-t', '--title', help='Title', required=True)

    return parser.parse_args()

def getdvdtype():
    """ Queries OMDbapi.org for title information and parses if it's a movie
        or a tv series """
    dvd_title = args.title

    year = dvd_title[(dvd_title.rindex('(')):len(dvd_title)]
    year = re.sub('[()]','', year)

    dvd_title = dvd_title[0:(dvd_title.rindex('('))].strip()
    dvd_title = cleanupstring(dvd_title)

    if year is None:
        year = ""
    
    dvd_title_info_json = urllib.request.urlopen("http://www.omdbapi.com/?t={0}&y={1}&plot=short&r=json".format(dvd_title, year)).read()
    doc = json.loads(dvd_title_info_json.decode())

    return doc['Type']


def cleanupstring(string):
    # clean up title string to pass to OMDbapi.org
    return re.sub('[_ ]',"+",string)

args = entry()

    
try:
    dvd_type = getdvdtype()
except:
    print("fail")
else:
    # we only want "movie" or "series"
    if dvd_type == "movie" or dvd_type == "series":
        print(dvd_type)
    else:
        print("other")