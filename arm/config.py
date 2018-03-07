#!/usr/bin/python3

# import os
# import re
import yaml

yamlfile = "/etc/arm/arm.yaml"
# cfgfile = "/etc/arm/arm.conf"

# if os.path.exists(yamlfile):
#     try:
#         os.remove(yamlfile)
#     except OSError:
#         err = "Could not delete .yaml path at:  " + yamlfile + " Probably a permissions error.  Exiting"
#         print(err)
#         raise ValueError(err, "config")


# with open(cfgfile, 'r') as f:
#     with open(yamlfile, 'w') as of:
#         for line in f:
#             if '#' not in line and line.strip():
#                 # print(line.strip())
#                 line = re.sub("true", "\"true\"", line)
#                 line = re.sub("false", "\"false\"", line)
#                 line = re.sub("=", ": ", line, 1)
#                 of.writelines(line)

with open(yamlfile, "r") as f:
    cfg = yaml.load(f)
