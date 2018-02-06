#!/usr/bin/python3

import os
import re
import yaml

yamlpath = "/tmp/arm_config.yaml"

if os.path.exists(yamlpath):
    try:
        os.remove(yamlpath)
    except OSError:
        err = "Could not delete .yaml path at:  " + yamlpath + " Probably a permissions error.  Exiting"
        print(err)
        raise ValueError(err,"config")


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
