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

    flake_config = "--max-complexity=15 --max-line-length=120 --show-source --statistics"

    # Run flake8 against ARM - arm
    armui.run_command(f"flake8 {arm_path}/arm {flake_config}",
                      f"ARM QA check completed against {arm_path}/arm")

    # Run flake8 against ARM - test
    armui.run_command(f"flake8 {arm_path}/test {flake_config}",
                      f"ARM QA check completed against {arm_path}/test")

    # Run flake8 against ARM - devtools
    armui.run_command(f"flake8 {arm_path}/devtools {flake_config}",
                      f"ARM QA check completed against {arm_path}/devtools")

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

    # unittest - ripper
    armui.run_command("python3 -m unittest discover -s /opt/arm/test/unittest -p 'test_ripper*.py' -v",
                      "ARM ripper unittest completed")

    # unittest - ui
    # todo: add flask unittesting in here

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
