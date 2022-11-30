#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Automatic-Ripping-Machine Development Tools"""

import os
import argparse
import armui
import log
import database


# global variables
__version__ = '0.1'
arm_home = "/home/arm"
arm_install = "/opt/arm"


# Dev Tools help output
#  INPUT: None
#  OUTPUT: to console
def help():
    print("Automatic Ripping Machine Development Tool Scripts\n")
    print("Usage: armdevtools [options]")
    print("OPTIONS:")
    print("-b \t Name of the branch to move to, example -b v2_devel")
    print("-d \t Clear the arm home folder, remove all directories and files")
    print("-h \t This help")
    print("-v \t Version")


# Change the git repository branch to another
#  INPUT: git_branch
#  OUTPUT: none
def git_branch_change(git_branch):
    if git_branch:
        log.info(f"Change the current git branch to - {git_branch}")
        # Stop the UI to avoid issues
        armui.stop()

        os.system(f"cd {arm_install}")
        try:
            os.system(f"git checkout {git_branch}")
            log.info(f"ARM branch: {git_branch} checked out")

            # Restart the UI once git has worked
            armui.start()
        except Exception as error:
            log.error(f"Something has gone wrong, unable to check out {git_branch}")
            log.error(f" - {error}")
            log.info("ARM UI currently stopped, fix git error then restart ARM UI")

    else:
        log.error("No branch has been provided")


# Clear data from the ARM home directory
#  INPUT: git_branch
#  OUTPUT: none
def arm_clear_data():
    # todo, read the location from the arm config file
    log.console(f"remove data from the home folder: {arm_home}")


# Commence reading from the input options
desc = "Automatic Ripping Machine Development Tool Scripts"
parser = argparse.ArgumentParser(description=desc)
parser.add_argument("-b", help="Name of the branch to move to, example -b v2_devel")
parser.add_argument("-d",
                    help="Clear the arm home folder, remove all directories and files",
                    action='store_true')
parser.add_argument("-db_rem",
                    help="Database tool - remove current arm.db file",
                    action='store_true')
parser.add_argument("-db_roll",
                    help="Database tool - roll the current database back a version," +
                    "input number of versions to roll back.")
parser.add_argument("-db_data",
                    help="Database tool - populate the database with Lorem Ipsum data. " +
                    "Requires the active database to be the most current",
                    action='store_true')
parser.add_argument("-v", help="ARM Dev Tools Version",
                    action='version',
                    version='%(prog)s {version}'.format(version=__version__))

args = parser.parse_args()
# -b move to branch
if args.b:
    git_branch_change(args.b)

# -d Delete/Clear arm home drive data
if args.d:
    arm_clear_data()

# -db_rem Database remove
if args.db_rem:
    database.remove()

# -db_roll Database rollback
if args.db_roll:
    database.roll(args.db_roll)

# -db_data Database data insert
if args.db_data:
    database.data()
