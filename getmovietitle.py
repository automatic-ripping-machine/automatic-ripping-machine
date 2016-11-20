#!/usr/bin/python

import argparse
import pydvdid

parser = argparse.ArgumentParser(description='hello')
parser.add_argument('-p','--path', help='Mount path to disc',required=True)

args = parser.parse_args()

crc64=pydvdid.compute(args.path)

print str(crc64)


