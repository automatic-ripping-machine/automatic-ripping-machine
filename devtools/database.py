#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Automatic-Ripping-Machine Development Tools
    ARM UI management tools
"""

import os
import sys
import log


# Remove the current ARM database file
#  INPUT: none
#  OUTPUT: none
def remove():
    # todo, make this do something
    log.info("remove the arm db file")


# Roll back the current arm.db file
#  INPUT: roll_back int
#  OUTPUT: none
def roll(num):
    # todo, make this do something
    log.info(f"roll back {num} versions")


# Populate the current database with dummy test data
#  INPUT: none
#  OUTPUT: none
def data():
    # todo, make this do something
    log.info("insert some data into the db")
