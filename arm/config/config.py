#!/usr/bin/python3
"""yaml config loader"""
import json
import os
import shutil
import yaml

import arm.config.config_utils as config_utils

arm_config: dict[str, str]
arm_config_path: str = os.environ.get("ARM_CONFIG_FILE", "/etc/arm/config/arm.yaml")

abcde_config: dict[str, str]
abcde_config_path: str

apprise_config: dict[str, str]
apprise_config_path: str


def _load_config(fp):
    with open(fp, "r") as yaml_file:
        config = yaml.safe_load(yaml_file)
    return config


def _load_abcde(fp):
    with open(fp, "r") as abcde_read_file:
        config = abcde_read_file.read()
    return config


def _render_config(config, comments):
    """Build the text of arm.yaml, with the comments from comments.json"""
    arm_cfg = comments["ARM_CFG_GROUPS"]["BEGIN"] + "\n\n"
    for key, value in dict(config).items():
        # Add any grouping comments
        arm_cfg += config_utils.arm_yaml_check_groups(comments, key)
        # Check for comments for this key in comments.json, add them if they exist
        try:
            if comment := comments[str(key)]:
                arm_cfg += f"\n{comment}\n"
        except KeyError:
            arm_cfg += "\n"
        if value is None:
            # str(None) would be written as the string "None"
            arm_cfg += f"{key}: null\n"
            continue
        # test if key value is an int
        value = str(value)  # just change the type to keep things as expected
        try:
            post_value = int(value)
            arm_cfg += f"{key}: {post_value}\n"
        except ValueError:
            # Test if value is Boolean
            arm_cfg += config_utils.arm_yaml_test_bool(key, value)
    return arm_cfg


def write_config_file(path, text):
    """
    Replace the file at ``path`` with ``text`` without leaving it empty or
    half-written: write a temporary file next to it, then rename it over.
    Falls back to writing in place if the rename isn't possible (e.g. the
    file itself is a bind mount).
    """
    tmp_path = f"{path}.tmp-{os.getpid()}"
    try:
        with open(tmp_path, "w") as tmp_file:
            tmp_file.write(text)
        if os.path.exists(path):
            shutil.copymode(path, tmp_path)
        os.replace(tmp_path, path)
    except OSError:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        with open(path, "w") as config_file:
            config_file.write(text)


def _repair_none_strings(config, template):
    """
    Earlier versions wrote empty (null) settings back as the string "None".
    Turn those back into None where the template's default is null.

    :return: True if anything was repaired
    """
    repaired = False
    for key, default in template.items():
        if default is None and config.get(key) == "None":
            config[key] = None
            repaired = True
    return repaired


def _update_config_file(path, user_config, template, config, comments_path):
    """
    Rewrite the user's arm.yaml only when it's missing settings from the
    template (migration) or needed a repair; leave it alone otherwise.

    :return: True if the file was rewritten
    """
    repaired = _repair_none_strings(config, template)
    if not (repaired or set(template) - set(user_config)):
        return False
    try:
        with open(comments_path, "r") as comments_file:
            comments = json.load(comments_file)
        # Build the whole file before touching the old one
        text = _render_config(config, comments)
        write_config_file(path, text)
    except (OSError, KeyError, ValueError):
        # Read-only config or a broken comments.json: keep the existing file
        return False
    return True


# arm config, open and read yaml contents
# handle arm.yaml migration here
# Load user config
cur_cfg = _load_config(arm_config_path)
# Load template config
template_config = _load_config(os.path.join(cur_cfg["INSTALLPATH"], "setup/arm.yaml"))

# Update the template config with the user's values
arm_config = dict(template_config)
arm_config.update(cur_cfg)

_update_config_file(arm_config_path, cur_cfg, template_config, arm_config,
                    os.path.join(cur_cfg["INSTALLPATH"], "arm/ui/comments.json"))

# abcde config file, open and read contents
abcde_config_path = arm_config["ABCDE_CONFIG_FILE"]
abcde_config = _load_abcde(abcde_config_path)

# apprise config, open and read yaml contents
apprise_config_path = arm_config["APPRISE"] or "/etc/arm/config/apprise.yaml"
try:
    apprise_config = _load_config(apprise_config_path)
except OSError:
    apprise_config = {}
