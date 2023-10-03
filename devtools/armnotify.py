#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Automatic-Ripping-Machine Development Tools
    ARM Notify test tools
"""

import log
from arm.ripper import utils
from arm.models.models import Job


def test():
    """
    Run a notification
        INPUT: none
        OUTPUT: none
    """
    try:
        job = Job("/dev/null")
        utils.notify(job, "ARM notification", "This is a notification by the ARM-Notification Test!")
    except Exception as error:
        log.error(f"ARM Notify failed to run - {error}")
