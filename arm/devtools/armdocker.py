#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Automatic-Ripping-Machine Development Tools
    Docker update and rebuild
"""

import armui
import log


def docker_rebuild(docker_run_path, arm_install):
    """
    Run quality check against the ARM code and output
        INPUT: path to conduct the check against
        OUTPUT: to cli
    """

    log.info("Rebuilding docker image post ARM update")

    # Stop ARM container
    armui.run_command("docker stop automatic-ripping-machine", "ARM container stopped")

    # Remove the ARM container
    armui.run_command("docker container rm automatic-ripping-machine", "ARM Docker container deleted")

    # ARM rebuild
    armui.run_command(f"docker build -t automatic-ripping-machine {arm_install}", "ARM Docker container rebuilt")

    # Start the new container
    armui.run_command(f"{docker_run_path}", "ARM Docker container running")
