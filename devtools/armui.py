#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Automatic-Ripping-Machine Development Tools
    ARM UI management tools
"""

import os
import log


# Stop the ARM UI
#  INPUT: none
#  OUTPUT: none
def stop():
    try:
        log.info("Going to stop ARMUI - requesting sudo")
        os.system("sudo systemctl stop armui.service")
        log.success("ARM UI stopped")
    except Exception as error:
        log.error(f"ARM UI unable to stop - {error}")


# Start the ARM UI
#  INPUT: none
#  OUTPUT: none
def start():
    try:
        log.info("Going to restart ARMUI - requesting sudo")
        os.system("sudo systemctl start armui.service")
        log.success("ARM UI started")
    except Exception as error:
        log.error(f"ARM UI unable to start - {error}")
