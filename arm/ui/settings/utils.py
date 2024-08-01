"""
ARM Utilities Functions for:
    Settings

Functions
    - get_git_revision_hash - Get hash of current git revision
    - git_check_updates - check for updates from git repository
    - generate_comments - generate comments about changes in git repository
    - build_arm_cfg - build ARM configuration
"""
import os
import json
import subprocess
import re
from flask import current_app as app

from config import config as cfg
from config import config_utils


def get_git_revision_hash() -> str:
    """
    Get full hash of current git commit
    """
    git_hash: str = 'unknown'
    try:
        git_hash = subprocess.check_output(['git', 'rev-parse', 'HEAD'],
                                           cwd=cfg.arm_config['INSTALLPATH']).decode('ascii').strip()
        # Trunkate to seven characters (aligns with the github commit values reported)
        git_hash = git_hash[:7]
        app.logger.debug(f"GIT revision: {git_hash}")
    except subprocess.CalledProcessError as e:
        app.logger.debug(f"GIT revision error: {e}")

    return git_hash


def git_check_updates(current_hash) -> bool:
    """
    Check if we are on the latest commit
    """
    git_update = subprocess.run(['git', 'fetch',
                                 'https://github.com/automatic-ripping-machine/automatic-ripping-machine'],
                                cwd=cfg.arm_config['INSTALLPATH'], check=False)
    git_log = subprocess.check_output('git for-each-ref refs/remotes/origin --sort="-committerdate" | head -1',
                                      shell=True, cwd="/opt/arm").decode('ascii').strip()
    app.logger.debug(git_update.returncode)
    app.logger.debug(git_log)
    app.logger.debug(current_hash)
    app.logger.debug(bool(re.search(rf"\A{current_hash}", git_log)))
    return bool(re.search(rf"\A{current_hash}", git_log))


def generate_comments():
    """
    load comments.json and use it for settings page
    allows us to easily add more settings later
    :return: json
    """
    comments_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "comments.json")
    try:
        with open(comments_file, "r") as comments_read_file:
            try:
                comments = json.load(comments_read_file)
            except Exception as error:
                app.logger.debug(f"Error with comments file. {error}")
                comments = "{'error':'" + str(error) + "'}"
    except FileNotFoundError:
        comments = "{'error':'File not found'}"
    return comments


def build_arm_cfg(form_data, comments):
    """
    Main function for saving new updated arm.yaml\n
    :param form_data: post-data
    :param comments: comments file loaded as dict
    :return: full new arm.yaml as a String
    """
    app.logger.debug(comments)
    arm_cfg = comments['ARM_CFG_GROUPS']['BEGIN'] + "\n\n"
    # This is not the safest way to do things.
    # It assumes the user isn't trying to mess with us.
    # This really should be hard coded.
    app.logger.debug("save_settings: START")
    for key, value in form_data.items():
        app.logger.debug(f"save_settings: current key {key} = {value} ")
        if key == "csrf_token":
            continue
        # Add any grouping comments
        arm_cfg += config_utils.arm_yaml_check_groups(comments, key)
        # Check for comments for this key in comments.json, add them if they exist
        try:
            arm_cfg += "\n" + comments[str(key)] + "\n" if comments[str(key)] != "" else ""
        except KeyError:
            arm_cfg += "\n"
        # test if key value is an int
        try:
            post_value = int(value)
            arm_cfg += f"{key}: {post_value}\n"
        except ValueError:
            # Test if value is Boolean
            arm_cfg += config_utils.arm_yaml_test_bool(key, value)
    app.logger.debug("save_settings: FINISH")
    return arm_cfg


def build_apprise_cfg(form_data):
    """
    Main function for saving new updated apprise.yaml\n
    :param form_data: post data
    :return: full new arm.yaml as a String
    """
    # This really should be hard coded.
    app.logger.debug("save_apprise: START")
    apprise_cfg = "\n\n"
    for key, value in form_data.items():
        app.logger.debug(f"save_apprise: current key {key} = {value} ")
        if key == "csrf_token":
            continue
        # test if key value is an int
        try:
            post_value = int(value)
            apprise_cfg += f"{key}: {post_value}\n"
        except ValueError:
            # Test if value is Boolean
            apprise_cfg += config_utils.arm_yaml_test_bool(key, value)
    app.logger.debug("save_apprise: FINISH")
    return apprise_cfg


def git_get_updates() -> dict:
    """
    update arm
    """
    git_log = subprocess.run(['git', 'pull'], cwd=cfg.arm_config['INSTALLPATH'], check=False)
    return {'stdout': git_log.stdout, 'stderr': git_log.stderr,
            'return_code': git_log.returncode, 'form': 'ARM Update', "success": (git_log.returncode == 0)}
