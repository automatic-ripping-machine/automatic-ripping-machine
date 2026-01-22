#!/usr/bin/python3
"""yaml config loader"""
import json
import os

from sqlalchemy.engine import URL
import yaml

import arm.config.config_utils as config_utils

CONFIG_LOCATION = "/etc/arm/config"
arm_config_path = os.path.join(CONFIG_LOCATION, "arm.yaml")
abcde_config_path = os.path.join(CONFIG_LOCATION, "abcde.conf")
apprise_config_path = os.path.join(CONFIG_LOCATION, "apprise.yaml")


def _normalize_database_config(config):
    """Populate SQLAlchemy connection details from config values."""
    configured_url = (config.get("DATABASE_URL") or "").strip()
    if configured_url:
        config["SQLALCHEMY_DATABASE_URI"] = configured_url
        config["DATABASE_IS_FILE_BACKED"] = configured_url.startswith("sqlite")
        scheme = configured_url.split(":", 1)[0]
        config["DATABASE_ENGINE"] = scheme
    else:
        engine = (config.get("DATABASE_ENGINE") or "sqlite").strip()
        if not engine:
            engine = "sqlite"
        config["DATABASE_ENGINE"] = engine
        engine_lower = engine.lower()
        if engine_lower == "sqlite":
            db_file = config.get("DBFILE") or ""
            config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_file}"
            config["DATABASE_IS_FILE_BACKED"] = True
        else:
            username = (config.get("DATABASE_USER") or None)
            password = (config.get("DATABASE_PASSWORD") or None)
            host = (config.get("DATABASE_HOST") or None)
            raw_port = config.get("DATABASE_PORT")
            port = None
            if raw_port not in (None, ""):
                try:
                    port = int(str(raw_port).strip())
                except ValueError:
                    port = None
            database = (config.get("DATABASE_NAME") or None)
            options = (config.get("DATABASE_OPTIONS") or "").strip()
            query = None
            if options:
                query = {}
                for fragment in options.split("&"):
                    if "=" in fragment:
                        key, value = fragment.split("=", 1)
                        query[key] = value

            # URL.create expects username/password to be unquoted; SQLAlchemy handles encoding internally.
            try:
                uri = URL.create(
                    drivername=engine,
                    username=username,
                    password=password,
                    host=host,
                    port=port,
                    database=database,
                    query=query
                )
            except TypeError:
                # Fallback for SQLAlchemy versions not supporting "query" when None.
                uri = URL.create(
                    drivername=engine,
                    username=username,
                    password=password,
                    host=host,
                    port=port,
                    database=database
                )

            config["SQLALCHEMY_DATABASE_URI"] = str(uri)
            config["DATABASE_IS_FILE_BACKED"] = False

    backup_path = (config.get("DATABASE_BACKUP_PATH") or "").strip()
    if not backup_path:
        db_file = config.get("DBFILE") or ""
        if db_file:
            backup_path = os.path.join(os.path.dirname(db_file), "backups")
        else:
            backup_path = "/home/arm/db/backups/"
    config["DATABASE_BACKUP_PATH"] = backup_path


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
new_cfg = _load_config("/opt/arm/setup/arm.yaml")

# 2. If the dicts do not have the same number of keys
if len(cur_cfg) != len(new_cfg):
    # 3. Update new dict with current values
    for key in cur_cfg:
        if key in new_cfg:
            new_cfg[key] = cur_cfg[key]

    # 4. Save the dictionary
    with open("/opt/arm/arm/ui/comments.json", "r") as comments_file:
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
    with open(arm_config_path, "w") as settings_file:
        settings_file.write(arm_cfg)
        settings_file.close()

arm_config = _load_config(arm_config_path)
_normalize_database_config(arm_config)

# abcde config file, open and read contents
abcde_config = _load_abcde(abcde_config_path)

# apprise config, open and read yaml contents
apprise_config = _load_config(apprise_config_path)
