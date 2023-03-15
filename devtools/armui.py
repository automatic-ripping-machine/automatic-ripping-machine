#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Automatic-Ripping-Machine Development Tools
    ARM UI management tools
"""

import os
import log


def stop():
    """
    Stop the ARM UI
        INPUT: none
        OUTPUT: none
    """
    try:
        log.info("Going to stop ARMUI - requesting sudo")
        os.system("sudo systemctl stop armui.service")
        log.success("ARM UI stopped")
    except Exception as error:
        log.error(f"ARM UI unable to stop - {error}")


def start():
    """
    Stop the ARM UI
        INPUT: none
        OUTPUT: none
    """
    try:
        log.info("Going to restart ARMUI - requesting sudo")
        os.system("sudo systemctl start armui.service")
        log.success("ARM UI started")
    except Exception as error:
        log.error(f"ARM UI unable to start - {error}")


def run_command(command, statement):
    """
    Run os commands and check they run
        INPUT: STRING command, STRING statment
        OUTPUT: none
    """
    try:
        # Stop ARM container
        log.info("-------------------------------------")
        log.info(f"Executing: {command}")
        os.system(f"{command}")
        log.success(statement)

    except FileNotFoundError as error:
        log.info("\n-------------------------------------")
        log.error(f"Something has gone wrong in executing {command}")
        log.error(f" - {error}")
        log.info("ARM UI currently stopped, fix error then restart ARM UI")
        log.info("-------------------------------------")
        exit
