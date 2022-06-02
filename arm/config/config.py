#!/usr/bin/python3
"""yaml config loader"""
import os
import yaml

abcde_config_path = os.path.join("/etc/arm/config", ".abcde.yaml")
apprise_config_path = os.path.join("/etc/arm/config", "apprise.yaml")
arm_config_path = os.path.join("/etc/arm/config", "arm.yaml")

with open(arm_config_path, "r") as f:
    try:
        arm_config = yaml.load(f, Loader=yaml.FullLoader)
    except Exception:
        arm_config = yaml.safe_load(f)  # For older versions use this
