#!/usr/bin/python3
"""yaml config loader"""
import json
import os
import threading
import yaml

import arm.config.config_utils as config_utils

# Lock for atomic updates to arm_config (clear + update must not be
# interleaved with concurrent readers).
arm_config_lock = threading.Lock()

arm_config: dict[str, str]
arm_config_path: str = os.environ.get("ARM_CONFIG_FILE", "/etc/arm/config/arm.yaml")

abcde_config: dict[str, str]
abcde_config_path: str


def _load_config(fp):
    with open(fp, "r") as yaml_file:
        config = yaml.safe_load(yaml_file)
    return config


def _load_abcde(fp):
    with open(fp, "r") as abcde_read_file:
        config = abcde_read_file.read()
    return config


# arm config, open and read yaml contents
# handle arm.yaml migration here
# 1. Load both current and template arm.yaml
cur_cfg = _load_config(arm_config_path)
new_cfg = _load_config(os.path.join(cur_cfg['INSTALLPATH'], "setup/arm.yaml"))

# 2. If the dicts do not have the same number of keys
if len(cur_cfg) != len(new_cfg):
    # 3. Update new dict with current values
    for key in cur_cfg:
        if key in new_cfg:
            new_cfg[key] = cur_cfg[key]

    # 4. Save the dictionary
    with open(
            os.path.join(cur_cfg["INSTALLPATH"], "arm/data/comments.json"),
            "r",
    ) as comments_file:
        comments = json.load(comments_file)

    arm_cfg = comments['ARM_CFG_GROUPS']['BEGIN'] + "\n\n"
    for key, value in dict(new_cfg).items():
        # Add any grouping comments
        arm_cfg += config_utils.arm_yaml_check_groups(comments, key)
        # Check for comments for this key in comments.json, add them if they exist
        try:
            arm_cfg += "\n" + comments[str(key)] + "\n" if comments[str(key)] != "" else ""
        except KeyError:
            arm_cfg += "\n"
        # test if key value is an int
        value = str(value)  # just change the type to keep things as expected
        try:
            post_value = int(value)
            arm_cfg += f"{key}: {post_value}\n"
        except ValueError:
            # Test if value is Boolean
            arm_cfg += config_utils.arm_yaml_test_bool(key, value)

    # this handles the truncation
    try:
        with open(arm_config_path, "w") as settings_file:
            settings_file.write(arm_cfg)
    except OSError:
        pass  # config may be read-only (e.g. Docker bind-mount)

arm_config = _load_config(arm_config_path)

# abcde config file, open and read contents
abcde_config_path = arm_config["ABCDE_CONFIG_FILE"]
abcde_config = _load_abcde(abcde_config_path)


def get_db_uri() -> str:
    """Return the SQLAlchemy database connection URI.

    Priority order:
      1. ARM_DATABASE_URL env var (operator override; takes precedence
         over arm.yaml).
      2. arm.yaml DATABASE_URL key (operator config).
      3. sqlite:///<DBFILE> default (backwards compatible).

    Empty string env var or empty arm.yaml value is treated as unset,
    so the default is returned. This avoids the foot-gun where someone
    half-clears the override and lands on a malformed URI.
    """
    explicit = os.environ.get('ARM_DATABASE_URL') or arm_config.get('DATABASE_URL')
    if explicit:
        return explicit
    return 'sqlite:///' + arm_config['DBFILE']
