#!/usr/bin/python3

import os
# import re
import yaml

yamlfile = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../..", "arm.yaml")

with open(yamlfile, "r") as f:
    try:
        cfg = yaml.load(f, Loader=yaml.FullLoader)
    except Exception:
        cfg = yaml.safe_load(f)  # For older versions use this
