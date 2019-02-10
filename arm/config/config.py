#!/usr/bin/python3

# import os
# import re
import yaml

yamlfile = "/etc/arm/arm.yaml"

with open(yamlfile, "r") as f:
    cfg = yaml.load(f)
