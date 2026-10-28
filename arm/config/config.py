#!/usr/bin/python3
"""yaml config loader"""
import json
import os
import yaml

import arm.config.config_utils as config_utils

arm_config: dict[str, str]
arm_config_path: str = os.environ.get("ARM_CONFIG_FILE", "/etc/arm/config/arm.yaml")

abcde_config: str
abcde_config_path: str

whipper_config: str
whipper_config_path: str

apprise_config: dict[str, str]
apprise_config_path: str


def _load_config(fp):
    try:
        with open(fp, "r") as yaml_file:
            config = yaml.safe_load(yaml_file)
    except OSError:
        config = {}
    return config or {}


def _load_text_file(fp):
    try:
        with open(fp, "r") as read_file:
            config = read_file.read()
    except OSError:
        config = ""
    return config


_load_abcde = _load_text_file
_load_whipper = _load_text_file


# arm config, open and read yaml contents
# handle arm.yaml migration here
# Load user config
cur_cfg = _load_config(arm_config_path)

# Fallback paths for development/testing
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
install_path = cur_cfg.get("INSTALLPATH", "") if os.path.isdir(cur_cfg.get("INSTALLPATH", "")) else project_root

# Load template config
template_path = os.path.join(install_path, "setup/arm.yaml")
if not os.path.isfile(template_path):
    template_path = os.path.join(project_root, "setup/arm.yaml")

arm_config = _load_config(template_path)

# Update the template config with the user's values
arm_config.update(cur_cfg)

try:
    # Save the dictionary
    with open(arm_config_path, "w") as settings_file:
        comments_path = os.path.join(install_path, "arm/ui/comments.json")
        if not os.path.isfile(comments_path):
            comments_path = os.path.join(project_root, "arm/ui/comments.json")

        with open(comments_path, "r") as comments_file:
            comments = json.load(comments_file)

        arm_cfg = comments["ARM_CFG_GROUPS"]["BEGIN"] + "\n\n"
        for key, value in dict(arm_config).items():
            # Add any grouping comments
            arm_cfg += config_utils.arm_yaml_check_groups(comments, key)
            # Check for comments for this key in comments.json, add them if they exist
            try:
                if comment := comments[str(key)]:
                    arm_cfg += f"\n{comment}\n"
            except KeyError:
                arm_cfg += "\n"
            # test if key value is an int
            value = str(value)  # just change the type to keep things as expected
            try:
                post_value = int(value)
                arm_cfg += f"{key}: {post_value}\n"
            except ValueError:
                # Test if value is Boolean
                arm_cfg += config_utils.arm_yaml_test_bool(key, value)

        settings_file.write(arm_cfg)
        settings_file.close()
except OSError:
    pass

# whipper config file, open and read contents
whipper_config_path = arm_config.get("WHIPPER_CONFIG_FILE", "/etc/arm/config/whipper.conf")
whipper_config = _load_whipper(whipper_config_path)

# abcde config file (legacy support)
abcde_config_path = arm_config.get("ABCDE_CONFIG_FILE", "/etc/arm/config/abcde.conf")
abcde_config = _load_abcde(abcde_config_path)

# apprise config, open and read yaml contents
apprise_config_path = arm_config["APPRISE"] or "/etc/arm/config/apprise.yaml"
try:
    apprise_config = _load_config(apprise_config_path)
except OSError:
    apprise_config = {}
