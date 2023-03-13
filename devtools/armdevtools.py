#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Automatic-Ripping-Machine Development Tools"""

import argparse

import armgit
import database
import armdocker


__version__ = '0.1'
arm_home = "/home/arm"
arm_install = "/opt/arm"


# Commence reading from the input options
desc = "Automatic Ripping Machine Development Tool Scripts"
parser = argparse.ArgumentParser(description=desc)
parser.add_argument("-b",
                    help="Name of the branch to move to, example -b v2_devel")
parser.add_argument("-d",
                    help="Clear the arm home folder, remove all directories and files",
                    action='store_true')
parser.add_argument("-dr",
                    help="Docker rebuild post ARM code update. Requires docker run script path to run.")
parser.add_argument("-db_rem",
                    help="Database tool - remove current arm.db file",
                    action='store_true')
parser.add_argument("-db_data",
                    help="Database tool - populate the database with Lorem Ipsum data. " +
                    "Requires the active database to be the most current",
                    action='store_true')
parser.add_argument("-qa",
                    help="QA Checks - run Flake8 against ARM",
                    action='store_true')
parser.add_argument("-pr",
                    help="Actions to run prior to commiting a PR against ARM on github",
                    action="store_true")
parser.add_argument("-v", help="ARM Dev Tools Version",
                    action='version',
                    version='%(prog)s {version}'.format(version=__version__))

args = parser.parse_args()
# -b move to branch
if args.b:
    armgit.git_branch_change(args.b, arm_install)

# -d Delete/Clear arm home drive data
if args.d:
    armgit.arm_clear_data()

# -dr Docker ARM update and rebuild
if args.dr:
    armdocker.docker_rebuild(args.dr, arm_install)

# -db_rem Database remove
if args.db_rem:
    database.remove()

# -db_data Database data insert
if args.db_data:
    database.data()

# -qa Quality Checks against ARM
if args.qa:
    armgit.flake8(arm_install)

if args.pr:
    armgit.pr_update()
