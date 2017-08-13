#!/usr/bin/python3

import os
import re
import yaml


if os.path.exists("/opt/arm/arm/config.yaml"):
    os.remove("/opt/arm/arm/config.yaml")

with open("/opt/arm/config", 'r') as f:
    with open("/opt/arm/arm/config.yaml", 'w') as of:
        for line in f:
            if 'PYSTOP' in line:
                break
            elif not '#' in line and line.strip():
                # print(line.strip())
                line = re.sub("true", "\"true\"", line)
                line = re.sub("false", "\"false\"", line)
                line = re.sub("=", ": ", line,1)
                of.writelines(line)

with open("/opt/arm/arm/config.yaml", "r") as f:
    cfg = yaml.load(f)
