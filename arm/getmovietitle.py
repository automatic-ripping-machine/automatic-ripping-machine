#!/usr/bin/python3

import argparse
import urllib
import os
import datetime
import pydvdid
import unicodedata
import xmltodict
import sys
import re
import logging
import logger
import classes


def entry():
    """ Entry to program, parses arguments"""
    parser = argparse.ArgumentParser(description='Get Movie Title from DVD or Blu-Ray')
    parser.add_argument('-p', '--path', help='Mount path to disc', required=True)

    return parser.parse_args()

def getdvdtitle(disc):
    """ Calculates CRC64 for the DVD and calls Windows Media
        Metaservices and returns the Title and year of DVD """
    logging.debug("Entering getmovietitle.getdvdtitle. Disc: " + str(disc))

    crc64 = pydvdid.compute(str(disc.mountpoint))
    # crc64 = pydvdid.compute("/mnt/dev/sr1")
    logging.info("DVD CRC64 hash is: " + str(crc64))
    urlstring = "http://metaservices.windowsmedia.com/pas_dvd_B/template/GetMDRDVDByCRC.xml?CRC={0}".format(str(crc64))
    logging.debug(urlstring)
    dvd_info_xml = urllib.request.urlopen(
        "http://metaservices.windowsmedia.com/pas_dvd_B/template/GetMDRDVDByCRC.xml?CRC={0}".
        format(crc64)).read()

    doc = xmltodict.parse(dvd_info_xml)
    dvd_title = doc['METADATA']['MDR-DVD']['dvdTitle']
    dvd_release_date = doc['METADATA']['MDR-DVD']['releaseDate']

    # title + release year
    # return dvd_title + " (" + dvd_release_date.split()[0] + ")"
    return[dvd_title, dvd_release_date]

def getbluraytitle(disc):
    """ Get's Blu-Ray title by parsing XML in bdmt_eng.xml """
    with open(disc.mountpoint + '/BDMV/META/DL/bdmt_eng.xml', "rb") as xml_file:
        doc = xmltodict.parse(xml_file.read())


    bluray_title = doc['disclib']['di:discinfo']['di:title']['di:name']

    bluray_modified_timestamp = os.path.getmtime(disc.mountpoint + '/BDMV/META/DL/bdmt_eng.xml')
    bluray_year = (datetime.datetime.fromtimestamp(bluray_modified_timestamp).strftime('%Y'))

    bluray_title = unicodedata.normalize('NFKD', bluray_title).encode('ascii', 'ignore').decode()

    bluray_title = bluray_title.replace(' - Blu-rayTM', '')
    bluray_title = bluray_title.replace(' - BLU-RAYTM', '')
    bluray_title = bluray_title.replace(' - BLU-RAY', '')
    bluray_title = bluray_title.replace(' - Blu-ray', '')
    return (bluray_title, bluray_year)

def clean_for_filename(string):
    """ Cleans up string for use in filename """
    string = re.sub('\[(.*?)\]', '', string)
    string = re.sub( '\s+', ' ', string)
    string = string.replace(' : ',' - ')
    string = string.replace(': ',' - ')
    return re.sub('[^\w\-_\.\(\) ]', '', string)

#pylint: disable=C0103

def main(disc):
    # args = entry()

    # logfile = logger.setuplogging()
    disc.hasnicetitle = False
    try:
        disc_title, disc_year = getdvdtitle(disc)
        disc_title = clean_for_filename(disc_title)
        logging.info("getmovietitle dvd title found: " + disc_title + " : " + disc_year)
    except:
        disc_title, disc_year = getbluraytitle(disc)
        disc_title = clean_for_filename(disc_title)
        logging.info("getmovietitle bluray title found: " + disc_title + " : " + disc_year)
        # print(disc_title)
    else:
        logging.info(disc_title + " : " + disc_year)
        if disc_title:
            disc.hasnicetitle = True
        return(disc_title, disc_year)
