#!/usr/bin/python3
"""yaml config loader"""
import os
import yaml

CONFIG_LOCATION = "/etc/arm/config"
abcde_config_path = os.path.join(CONFIG_LOCATION, "abcde.conf")
apprise_config_path = os.path.join(CONFIG_LOCATION, "apprise.yaml")
arm_config_path = os.path.join(CONFIG_LOCATION, "arm.yaml")


def _load_config(fp):
    with open(fp, "r") as yaml_file:
        config = yaml.safe_load(yaml_file)
    return config


apprise_config = _load_config(apprise_config_path)
arm_config = _load_config(arm_config_path)
with open(abcde_config_path, "r") as abcde_read_file:
    abcde_config = abcde_read_file.read()
