#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Automatic-Ripping-Machine Development Tools
    ARM Notify test tools
"""

import log
import sys
sys.path.insert(0, '/opt/arm')
from arm.ripper import utils        # noqa E402
from arm.models.job import Job   # noqa E402


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
