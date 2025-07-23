import os
import yaml
import json
CONFIG_LOCATION = "/etc/arm/config"
arm_config_path = os.path.join(CONFIG_LOCATION, "arm.yaml")
arm_config_path = "/etc/arm/config/arm.yaml"
comments = '../comments.json'

with open(arm_config_path, 'r') as armCfg:
    config = yaml.safe_load(armCfg)

with open(comments, 'r') as cmntsFile:
    comments = json.load(cmntsFile)

newConfig = {}
for key, value in config.items():
    
    # Just in case the comment is empty, we will get the value for it, and
    # if none, set it to string
    comm_value = comments.get(key)
    if comm_value is None: comm_value = ""
    newConfig[key] = {
        "defaultForInternalUse": value,
        "commentForInternalUse": comm_value,
        "dataValidation": "",
        "formFieldType": str(type(value))
    }

print(len(newConfig))
with open('./ripperFormConfig.json', 'w') as jsonFile:
    json.dump(newConfig, jsonFile, indent=4)


    