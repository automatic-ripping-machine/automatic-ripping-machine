"""File to hold all functions pertaining to apprise"""
import logging
import apprise

import arm.config.config as cfg


# The key within the global configuration for apprise
APPRISE_CONFIG_KEY = "APPRISE"


def get_apprise_config_path():
    # Rather than optinoally support apprise, we should assume apprise
    # even if the configuration has no notificiation endpoints
    path = cfg.arm_config.get(APPRISE_CONFIG_KEY)
    if path == "":
        return None
    return path


def load_config():
    """Load apprise's configuration, if it exists. Else, None"""
    if get_apprise_config_path():
        with open(get_apprise_config_path()) as fin:
            return fin.read()
    return None


def test_config(prospective):
    """Return whether a prospective configuration is valid."""
    apprise_config = apprise.AppriseConfig()
    return apprise_config.add_config(prospective)


def save_config(updated):
    """Persist the provided configuration. Returns True if successful, else False"""
    if not get_apprise_config_path():
        logging.error("Apprise configuration not set, cannot save config")
        return False
    if not test_config(updated):
        logging.error("Provided apprise configuration invalid")
        return False
    with open(get_apprise_config_path(), "w+") as fout:
        fout.write(updated)


def notify(title, body):
    """
    APPRISE NOTIFICATIONS\n
    :param title: the message title
    :param body: the main body of the message
    :return: True for successful notification, else False
    """
    apprise_config = load_config()
    logging.debug(f"Apprise notification | title: '{title}' | body: '{body}'")
    if not apprise_config:
        logging.error("Apprise configuration not set, skipping notification")
        return False
    if not test_config(apprise_config):
        logging.error("Apprise configuration invalid, skipping notification")
        return False

    apobj = apprise.Apprise()
    config = apprise.AppriseConfig()
    config.add(get_apprise_config_path())
    apobj.add(config)
    try:
        apobj.notify(
            body=body,
            title=title,
            tag='arm'
        )
        logging.debug("Apprise notification was successful")
    except Exception:  # noqa: E722
        logging.exception("Failed sending apprise notification")
        return False

    return True
