#!/usr/bin/python3

import argparse
import urllib
import os
import datetime
import pydvdid
import unicodedata
import xmltodict
import sys # noqa # pylint: disable=unused-import
import re
import logging
import logger # noqa # pylint: disable=unused-import
import classes # noqa # pylint: disable=unused-import


def entry():
    """ Entry to program, parses arguments"""
    parser = argparse.ArgumentParser(description='Get Movie Title from DVD or Blu-Ray')
    parser.add_argument('-p', '--path', help='Mount path to disc', required=True)

    return parser.parse_args()


def getdvdtitle(disc):
    """ Calculates CRC64 for the DVD and calls Windows Media
        Metaservices and returns the Title and year of DVD """
    logging.debug(str(disc))

    try:
        crc64 = pydvdid.compute(str(disc.mountpoint))
    except pydvdid.exceptions.PydvdidException as e:
        logging.error("Pydvdid failed with the error: " + str(e))

    logging.info("DVD CRC64 hash is: " + str(crc64))
    urlstring = "http://metaservices.windowsmedia.com/pas_dvd_B/template/GetMDRDVDByCRC.xml?CRC={0}".format(str(crc64))
    logging.debug(urlstring)

    try:
        dvd_info_xml = urllib.request.urlopen(
            "http://metaservices.windowsmedia.com/pas_dvd_B/template/GetMDRDVDByCRC.xml?CRC={0}".
            format(crc64)).read()
    except OSError:
        logging.error("Failed to reach windowsmedia web service")
        return[None, None]

    try:
        doc = xmltodict.parse(dvd_info_xml)
        dvd_title = doc['METADATA']['MDR-DVD']['dvdTitle']
        dvd_release_date = doc['METADATA']['MDR-DVD']['releaseDate']
        dvd_title = dvd_title.strip()
        dvd_release_date = dvd_release_date.split()[0]
    except KeyError:
        logging.error("Windows Media request returned no result.  Likely the DVD is not in their database.")
        return[None, None]

    return[dvd_title, dvd_release_date]


def getbluraytitle(disc):
    """ Get's Blu-Ray title by parsing XML in bdmt_eng.xml """
    try:
        with open(disc.mountpoint + '/BDMV/META/DL/bdmt_eng.xml', "rb") as xml_file:
            doc = xmltodict.parse(xml_file.read())
    except OSError:
        logging.error("Disc is a bluray, but bdmt_eng.xml could not be found.  Disc cannot be identified.")
        return[None, None]

    try:
        bluray_title = doc['disclib']['di:discinfo']['di:title']['di:name']
    except KeyError:
        logging.error("Could not parse title from bdmt_eng.xml file.  Disc cannot be identified.")
        return[None, None]

    bluray_modified_timestamp = os.path.getmtime(disc.mountpoint + '/BDMV/META/DL/bdmt_eng.xml')
    bluray_year = (datetime.datetime.fromtimestamp(bluray_modified_timestamp).strftime('%Y'))

    bluray_title = unicodedata.normalize('NFKD', bluray_title).encode('ascii', 'ignore').decode()

    bluray_title = bluray_title.replace(' - Blu-rayTM', '')
    bluray_title = bluray_title.replace(' Blu-rayTM', '')
    bluray_title = bluray_title.replace(' - BLU-RAYTM', '')
    bluray_title = bluray_title.replace(' - BLU-RAY', '')
    bluray_title = bluray_title.replace(' - Blu-ray', '')
    return (bluray_title, bluray_year)


def clean_for_filename(string):
    """ Cleans up string for use in filename """
    string = re.sub(r'\[(.*?)\]', '', string)
    string = re.sub(r'\s+', ' ', string)
    string = string.replace(' : ', ' - ')
    string = string.replace(': ', ' - ')
    string = string.strip()
    return re.sub(r'[^\w\-_\.\(\) ]', '', string)

# pylint: disable=C0103


def main(disc):
    # args = entry()

    disc.hasnicetitle = False
    try:
        disc_title, disc_year = getdvdtitle(disc)
        if disc_title:
            disc_title = clean_for_filename(disc_title)
            logging.info("getmovietitle dvd title found: " + disc_title + " : " + disc_year)
        else:
            logging.warning("DVD title not found")
            disc_title = disc.label
            disc_year = "0000"
    except Exception:
        disc_title, disc_year = getbluraytitle(disc)
        if disc_title:
            disc_title = clean_for_filename(disc_title)
            logging.info("getmovietitle bluray title found: " + disc_title + " : " + disc_year)
            disc.hasnicetitle = True
        return(disc_title, disc_year)
    else:
        logging.info(str(disc_title) + " : " + str(disc_year))
        if disc_title:
            disc.hasnicetitle = True
        logging.info("Returning: " + str(disc_title) + ", " + str(disc_year))
        return(disc_title, disc_year)
