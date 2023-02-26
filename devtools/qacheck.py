#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Automatic-Ripping-Machine Development Tools
    Flake quality checks
"""

import os
import armui
import log


def flake8(arm_path):
    """
    Run quality check against the ARM code and output
        INPUT: none
        OUTPUT: to cli
    """
    log.info(f"Running quality checks against ARM - {arm_path}")
    # Stop the UI to avoid issues
    armui.stop()
    try:
        command = f"flake8 {arm_path}/arm --max-complexity=15 --max-line-length=120 --show-source --statistics"
        log.info(f"Executing: {command}")
        os.system(f"{command}")
        log.success("ARM QA check completed")

        # Restart the UI once git has worked
        armui.start()
    except Exception as error:
        log.error("Something has gone wrong, unable to run checks")
        log.error(f" - {error}")
        log.info("ARM UI currently stopped, fix error then restart ARM UI")
