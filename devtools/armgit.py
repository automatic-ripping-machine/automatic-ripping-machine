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
        INPUT: path to conduct the check against
        OUTPUT: to cli
    """
    # Stop the UI to avoid issues
    armui.stop()

    log.info(f"Running quality checks against ARM - {arm_path}")

    # Run flake8 against ARM
    armui.run_command(f"flake8 {arm_path}/arm --max-complexity=15 --max-line-length=120 --show-source --statistics",
                      "ARM QA check completed")

    # Restart the UI once git has worked
    armui.start()


def pr_update():
    """
    Run any commands required prior to raising a PR
        INPUT: none
        OUTPUT: to cli
    """
    # Stop the UI to avoid issues
    armui.stop()

    log.info("Running scripts to bring ARM up to date")

    # GIT submodule update
    armui.run_command("cd .. & git submodule update --remote", "ARM submodule updated")

    # Restart the UI once git has worked
    armui.start()


def git_branch_change(git_branch, arm_install):
    """Change the git repository branch to another
        INPUT: git_branch
        OUTPUT: none
    """
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


def arm_clear_data():
    """
    Clear data from the ARM home directory
        INPUT: git_branch
        OUTPUT: none
    """
    # todo, read the location from the arm config file
    # log.console(f"remove data from the home folder: {arm_home}")
    log.info("not currently supported")
