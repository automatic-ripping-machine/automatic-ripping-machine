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

    try:
        year = dvd_title[(dvd_title.rindex('(')):len(dvd_title)]
    except:
        year = ""
    else:
        year = re.sub('[()]','', year)

    try:
        dvd_title = dvd_title[0:(dvd_title.rindex('('))].strip()
    except:
        dvd_title_clean = cleanupstring(dvd_title)
    else:
        dvd_title_clean = cleanupstring(dvd_title)

    if year is None:
        year = ""

    dvd_type = callwebservice(dvd_title_clean, year)
    # print (dvd_type)

    # handle failures
    # this is kind of kludgy, but it kind of work...
    if (dvd_type == "fail"):

        # first try submitting without the year
        dvd_type = callwebservice(dvd_title_clean, "")
        # print (dvd_type)

        if (dvd_type != "fail"):
            #that means the year is wrong. 
            needs_new_year = "true"

        if (dvd_type == "fail"):
            # second see if there is a hyphen and split it
            if (dvd_title.find("-") > -1):
                dvd_title_slice = dvd_title[:dvd_title.find("-")]
                dvd_title_slice =cleanupstring(dvd_title_slice)
                dvd_type = callwebservice(dvd_title_slice)
                
            # if still fail, then try slicing off the last word in a loop
            while dvd_type == "fail" and dvd_title_clean.count('+') > 0:
                dvd_title_clean = dvd_title_clean.rsplit('+', 1)[0]
                dvd_type = callwebservice(dvd_title_clean)
        
    if needs_new_year == "true":
        #pass the new year back to bash to handle
        global new_year
        return dvd_type + "#" + new_year
    else:
        return dvd_type

def cleanupstring(string):
    # clean up title string to pass to OMDbapi.org
    string = string.strip()
    return re.sub('[_ ]',"+",string)

def callwebservice(dvd_title, year=""):
    """ Queries OMDbapi.org for title information and parses if it's a movie
        or a tv series """
    # print (dvd_title)

    try:
        dvd_title_info_json = urllib.request.urlopen("http://www.omdbapi.com/?t={0}&y={1}&plot=short&r=json".format(dvd_title, year)).read()
    except:
        return "fail"
    else:
        doc = json.loads(dvd_title_info_json.decode())
        if doc['Response'] == "False":
            return "fail"
        else:
            global new_year 
            new_year = doc['Year']
            return doc['Type']

args = entry()

dvd_type = getdvdtype()
print(dvd_type)
