#!/usr/bin/env python3
"""
Main code for setting up the logging for all of A.R.M
Also triggers CD identification
"""
# set up logging

import os
import logging
import logging.handlers
import time

import arm.config.config as cfg


short_format = (
    "%(levelname)s:"
    + (" %(module)s.%(funcName)s:" if cfg.arm_config["LOGLEVEL"] == "DEBUG" else "")
    + " %(message)s"
)
long_format = f"%(asctime)s ARM: {short_format}"

short_formatter = logging.Formatter(short_format, datefmt=cfg.arm_config["DATE_FORMAT"])
long_formatter = logging.Formatter(long_format, datefmt=cfg.arm_config["DATE_FORMAT"])


def setup_job_log(job):
    """
    Setup logging and return the path to the logfile for redirection of external calls\n
    We need to return the full logfile path but set the job.logfile to just the filename
    """
    # This isn't catching all of them
    if job.label == "" or job.label is None:
        if job.disctype == "music":
            valid_label = job.identify_audio_cd()
        else:
            valid_label = "no_label"
    else:
        valid_label = job.label.replace("/", "_")

    log_file_name = f"{valid_label}.log"
    new_log_file = f"{valid_label}_{job.stage}.log"
    temp_log_full = os.path.join(cfg.arm_config['LOGPATH'], log_file_name)
    log_file = new_log_file if os.path.isfile(temp_log_full) else log_file_name
    log_full = os.path.join(cfg.arm_config['LOGPATH'], log_file)

    job.logfile = log_file

    # If a more specific log file is created, the messages are not also logged to
    # arm.log, but they are still logged to stdout and syslog
    logger = logging.getLogger()
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler):
            logger.removeHandler(handler)

    logger.addHandler(_create_file_handler(log_file))

    # These stop apprise and others spitting our secret keys if users post log online
    logging.getLogger("apprise").setLevel(logging.WARN)
    logging.getLogger("requests").setLevel(logging.WARN)
    logging.getLogger("urllib3").setLevel(logging.WARN)

    # Return the full logfile location to the logs
    return log_full


def clean_up_logs(logpath, loglife):
    """
    Delete all log files older than {loglife} days\n
    if {loglife} is 0 don't delete anything\n
    :param logpath: path of log files\n
    :param loglife: days to let logs live\n
    :return:
    """
    if loglife < 1:
        logging.info("loglife is set to 0. Removal of logs is disabled")
        return False
    now = time.time()
    logging.info(f"Looking for log files older than {loglife} days old.")

    logs_folders = [logpath, os.path.join(logpath, 'progress')]
    # Loop through each log path
    for log_dir in logs_folders:
        logging.info(f"Checking path {log_dir} for old log files...")
        # Loop through each file in current folder and remove files older than set in arm.yaml
        if not os.path.isdir(log_dir):
            logging.info(f"{log_dir} is not a directory or doesn't exist. Skipping.")
            continue
        for filename in os.listdir(log_dir):
            fullname = os.path.join(log_dir, filename)
            if fullname.endswith(".log") and os.stat(fullname).st_mtime < now - loglife * 86400:
                logging.info(f"Deleting log file: {filename}")
                os.remove(fullname)
    return True


def _create_file_handler(filename):
    file_handler = logging.FileHandler(os.path.join(cfg.arm_config["LOGPATH"], filename))
    file_handler.setFormatter(long_formatter)
    return file_handler


def create_early_logger(stdout=True, syslog=True, file=True):
    """
    From: https://gist.github.com/danielkraic/a1657f19bad9c158cbf9532e1ed1503b\n
    Create logging object with logging to syslog, file and stdout\n
    Will log to `/var/log/arm.log`\n
    :param app_name: app name
    :param log_level: logging log level
    :param stdout: log to stdout
    :param syslog: log to syslog
    :param file: log to file
    :return: logging object
    """
    # disable requests logging
    # logging.getLogger("requests").setLevel(logging.ERROR)
    # logging.getLogger("urllib3").setLevel(logging.ERROR)

    # create logger
    logger = logging.getLogger("ARM")
    logger.setLevel(cfg.arm_config["LOGLEVEL"])

    if file:
        logger.addHandler(_create_file_handler("arm.log"))

    if syslog:
        # create syslog logger handler
        stream_handler = logging.handlers.SysLogHandler(address='/dev/log')
        stream_handler.setFormatter(short_formatter)
        logger.addHandler(stream_handler)

    if stdout:
        # create stream logger handler
        stream_print = logging.StreamHandler()
        stream_print.setFormatter(short_formatter)
        logger.addHandler(stream_print)

    return logger
