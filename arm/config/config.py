#!/usr/bin/python3

import os
import yaml

yamlfile = os.path.join("/etc/arm/config", "arm.yaml")

with open(yamlfile, "r") as f:
    try:
        cfg = yaml.load(f, Loader=yaml.FullLoader)
    except Exception:
        cfg = yaml.safe_load(f)  # For older versions use this
