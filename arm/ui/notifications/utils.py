"""
ARM Utilities Functions for:
    Notifications

Functions
    - notify - Send a notification using apprise
"""
import apprise
import subprocess
from flask import current_app as app

from ui.notifications.apprise_bulk import apprise_notify
from ui import db
from config import config as cfg
from models.notifications import Notifications


def notify(job, title: str, body: str):
    """
    Send notifications with apprise\n
    :param job: Current Job
    :param title: title for notification
    :param body: body of the notification
    :return: None
    """

    # Prepend Site Name if configured
    if cfg.arm_config["ARM_NAME"] != "":
        title = f"[{cfg.arm_config['ARM_NAME']}] - {title}"

    # append Job ID if configured
    if cfg.arm_config["NOTIFY_JOBID"] and job is not None:
        title = f"{title} - {job.job_id}"

    # Send to local db
    app.logger.debug(f"apprise message, title: {title} body: {body}")
    notification = Notifications(title, body)
    db.session.add(notification)
    db.session.commit()

    bash_notify(cfg.arm_config, title, body)

    # Sent to remote sites
    # Create an Apprise instance
    apobj = apprise.Apprise()
    if cfg.arm_config["PB_KEY"] != "":
        apobj.add('pbul://' + str(cfg.arm_config["PB_KEY"]))
    if cfg.arm_config["IFTTT_KEY"] != "":
        apobj.add('ifttt://' + str(cfg.arm_config["IFTTT_KEY"]) + "@" + str(cfg.arm_config["IFTTT_EVENT"]))
    if cfg.arm_config["PO_USER_KEY"] != "":
        apobj.add('pover://' + str(cfg.arm_config["PO_USER_KEY"]) + "@" + str(cfg.arm_config["PO_APP_KEY"]))
    if cfg.arm_config["JSON_URL"] != "":
        apobj.add(str(cfg.arm_config["JSON_URL"]).replace("http://", "json://").replace("https://", "jsons://"))
    try:
        apobj.notify(body, title=title)
    except Exception as error:  # noqa: E722
        app.logger.error(f"Failed sending notifications. error:{error}. Continuing processing...")

    # Bulk send notifications, using the config set on the ripper config page
    if cfg.arm_config["APPRISE"] != "":
        try:
            apprise_notify(cfg.arm_config["APPRISE"], title, body)
            app.logger.debug(f"apprise-config: {cfg.arm_config['APPRISE']}")
        except Exception as error:  # noqa: E722
            app.logger.error(f"Failed sending apprise notifications. {error}")


def bash_notify(cfg, title, body):
    # bash notifications use subprocess instead of apprise.
    if cfg['BASH_SCRIPT'] != "":
        try:
            subprocess.run(["/usr/bin/bash", cfg['BASH_SCRIPT'], title, body])
            app.logger.debug("Sent bash notification successful")
        except Exception as error:  # noqa: E722
            app.logger.error(f"Failed sending notification via bash. Continuing  processing...{error}")
