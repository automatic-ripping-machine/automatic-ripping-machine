#!/usr/bin/python

import argparse
import pydvdid
import urllib
# import libxml2
import xmltodict

parser = argparse.ArgumentParser(description='hello')
parser.add_argument('-p','--path', help='Mount path to disc',required=True)
args = parser.parse_args()

crc64=pydvdid.compute(args.path)
dvd_info_xml = urllib.urlopen("http://metaservices.windowsmedia.com/pas_dvd_B/template/GetMDRDVDByCRC.xml?CRC={0}".format(crc64)).read()

doc = xmltodict.parse(dvd_info_xml)
dvd_title = doc['METADATA']['MDR-DVD']['dvdTitle']
dvd_release_date = doc['METADATA']['MDR-DVD']['releaseDate']

# title + release year
print dvd_title + " (" + dvd_release_date.split()[0] + ")"
