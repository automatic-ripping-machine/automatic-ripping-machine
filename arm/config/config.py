#!/usr/bin/python3

import os
import yaml

default_yamlfile = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../..", "arm.yaml")

for yamlfile in [os.path.expanduser('~/.config/arm/arm.yaml'),
                 '/etc/arm/arm.yaml', default_yamlfile]:
    if not os.path.exists(yamlfile):
        continue

    with open(yamlfile, "r") as f:
        try:
            cfg = yaml.load(f, Loader=yaml.FullLoader)
        except Exception:
            cfg = yaml.safe_load(f)  # For older versions use this

        break
