#!/usr/bin/python3
"""yaml config loader"""
import os
import yaml

abcde_config_path = os.path.join("/etc/arm/config", ".abcde.conf")
apprise_config_path = os.path.join("/etc/arm/config", "apprise.yaml")
arm_config_path = os.path.join("/etc/arm/config", "arm.yaml")


def _load_config(fp):
    with open(fp, "r") as yaml_file:
        config = yaml.safe_load(yaml_file)
    return config


apprise_config = _load_config(apprise_config_path)
arm_config = _load_config(arm_config_path)
