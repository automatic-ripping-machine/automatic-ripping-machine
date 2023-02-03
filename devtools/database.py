#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Automatic-Ripping-Machine Development Tools
    ARM UI management tools
"""

import os
import armui
import log

# DB variables
arm_home = "/home/arm"
path_db = arm_home + "/db/"
file_db = "arm.db"


def remove():
    """
    Remove the current ARM database file
        INPUT: none
        OUTPUT: none
    """
    log.info("Removing the ARM DB file")
    # Stop the UI to avoid issues
    armui.stop()
    try:
        os.system(f"rm {path_db}{file_db}")
        log.success(f"ARM DB {path_db}{file_db} removed")

        # Restart the UI once git has worked
        armui.start()
    except Exception as error:
        log.error(f"Something has gone wrong, unable to remove {path_db}{file_db}")
        log.error(f" - {error}")
        log.info("ARM UI currently stopped, fix git error then restart ARM UI")


def roll(num):
    """
    Roll back the current arm.db file
        INPUT: roll_back int
        OUTPUT: none
    """
    # todo, make this do something
    log.info(f"roll back {num} versions")
    log.info("not currently supported")


def data():
    """
    Populate the current database with dummy test data
        INPUT: none
        OUTPUT: none
    """
    # todo, make this do something
    # log.info("insert some data into the db")
    log.info("not currently supported")
