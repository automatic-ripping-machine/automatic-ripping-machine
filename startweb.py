#!/usr/bin/python3

import sys
# from .arm import config
from webserver import logserve

if __name__ == "__main__":
    from sys import argv

    if len(argv) == 2:
        logserve.run(port=int(argv[1]))
    else:
        logserve.run()