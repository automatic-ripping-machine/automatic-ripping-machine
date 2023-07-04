#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Automatic-Ripping-Machine Development Tools
    ARM UI management tools
"""

import os
import armui
import log
import datetime

# DB variables
arm_home = "/home/arm"
path_db = arm_home + "/db/"
file_db = "arm.db"
path_alembic = "/opt/arm/arm/migrations"


def remove():
    """
    Remove the current ARM database file
        INPUT: none
        OUTPUT: none
    """
    # Stop the UI to avoid issues
    armui.stop()

    log.info("Removing the ARM DB file")

    # Remove ARM DB file
    armui.run_command(f"rm {path_db}{file_db}", f"ARM DB {path_db}{file_db} removed")

    # Restart the UI once git has worked
    armui.start()


def database_backup():
    """
    Backup the arm database file, prior to removing
        INPUT: none
        OUTPUT: none
    """
    try:
        # backup the current ARM DB
        log.info("Backing up the current ARM DB")
        currentime = datetime.datetime.now()
        filename = f"arm_{currentime.year}-{currentime.month}-{currentime.day}_{currentime.hour}{currentime.minute}.db"
        os.system(f"mv {path_db}{file_db} {path_db}{filename}")
        log.success(f"current ARM DB saved {path_db}{filename}")
    except Exception as error:
        log.error("Something has gone wrong, unable backup the database")
        log.error(f" - {error}")


def data():
    """
    Populate the current database with dummy test data
        INPUT: none
        OUTPUT: none
    """
    # todo, make this do something
    # log.info("insert some data into the db")
    log.info("not currently supported")
