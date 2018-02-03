#!/usr/bin/python3

import os
import re
import yaml

yamlpath = "/tmp/arm_config.yaml"

if os.path.exists(yamlpath):
    os.remove(yamlpath)

with open("/opt/arm/config", 'r') as f:
    with open(yamlpath, 'w') as of:
        for line in f:
            if 'PYSTOP' in line:
                break
            elif not '#' in line and line.strip():
                # print(line.strip())
                line = re.sub("true", "\"true\"", line)
                line = re.sub("false", "\"false\"", line)
                line = re.sub("=", ": ", line,1)
                of.writelines(line)

with open(yamlpath, "r") as f:
    cfg = yaml.load(f)
