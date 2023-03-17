#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Automatic-Ripping-Machine Development Tools
    To support development of ARM, some of the more tedious and repetitious development tasks
    have been wrapped up into the ARM Development Tools. The developer tools (devtools)
    are designed to help out anyone contributing to ARM and save time when testing
    out any changes being made.
    More details are captured in the wiki
    https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/ARM-Development-Tools
"""

import argparse

import armgit
import database
import armdocker


__version__ = '0.2'
arm_home = "/home/arm"
arm_install = "/opt/arm"


# Commence reading from the input options
desc = "Automatic Ripping Machine Development Tool Scripts"
parser = argparse.ArgumentParser(description=desc)
parser.add_argument("-b",
                    help="Name of the branch to move to, example -b v2_devel")
parser.add_argument("-dr",
                    help="Docker rebuild post ARM code update. Requires docker run script path to run.")
parser.add_argument("-db_rem",
                    help="Database tool - remove current arm.db file",
                    action='store_true')
parser.add_argument("-qa",
                    help="QA Checks - run Flake8 against ARM",
                    action='store_true')
parser.add_argument("-pr",
                    help="Actions to run prior to committing a PR against ARM on github",
                    action="store_true")
parser.add_argument("-v", help="ARM Dev Tools Version",
                    action='version',
                    version='%(prog)s {version}'.format(version=__version__))

args = parser.parse_args()
# -b move to branch
if args.b:
    armgit.git_branch_change(args.b, arm_install)

# -dr Docker ARM update and rebuild
if args.dr:
    armdocker.docker_rebuild(args.dr, arm_install)

# -db_rem Database remove
if args.db_rem:
    database.remove()

# -qa Quality Checks against ARM
if args.qa:
    armgit.flake8(arm_install)

if args.pr:
    armgit.pr_update()
