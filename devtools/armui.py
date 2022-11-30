#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Automatic-Ripping-Machine Development Tools
    ARM UI management tools
"""

import os
import sys
import log


# Stop the ARM UI
#  INPUT: none
#  OUTPUT: none
def stop():
    try:
        os.system("sudo systemctl stop armui.service")
        log.info("ARM UI stopped")
    except:
        log.error("ARM UI unable to stop")


# Start the ARM UI
#  INPUT: none
#  OUTPUT: none
def start():
    try:
        os.system("sudo systemctl start armui.service")
        log.info("ARM UI started")
    except:
        log.error("ARM UI unable to start")
