#!/usr/bin/env python3
"""
Structured logging setup for A.R.M using structlog.

Uses structlog's ProcessorFormatter to intercept stdlib LogRecord objects
at the handler/formatter level. All existing logging.info()/error()/etc.
calls automatically produce structured output — zero changes needed in
the 200+ call sites across ARM source files.

Output targets:
  - FileHandler (per-job .log): JSON lines (machine-parseable)
  - StreamHandler (stdout):     colored human-readable (for docker logs)
  - SysLogHandler (/dev/log):   key=value pairs (compact text)
"""

import os
import logging
import logging.handlers
import time

import structlog

import arm.config.config as cfg

# Shared pre-processing chain for stdlib LogRecords.
# These run on every stdlib log record before the final renderer.
_foreign_pre_chain = [
    structlog.contextvars.merge_contextvars,
    structlog.stdlib.add_log_level,
    structlog.stdlib.add_logger_name,
    structlog.processors.TimeStamper(fmt="iso"),
]


def _configure_structlog():
    """One-time structlog configuration (idempotent)."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
    )


def _json_formatter():
    """ProcessorFormatter that renders JSON lines for file output."""
    return structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=_foreign_pre_chain,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(),
        ],
    )


def _console_formatter():
    """ProcessorFormatter that renders colored human-readable output."""
    return structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=_foreign_pre_chain,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.dev.ConsoleRenderer(colors=True),
        ],
    )


def _syslog_formatter():
    """ProcessorFormatter that renders compact key=value text for syslog."""
    return structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=_foreign_pre_chain,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.KeyValueRenderer(),
        ],
    )


def _create_file_handler(filename):
    """Create a FileHandler with JSON formatting."""
    file_handler = logging.FileHandler(
        os.path.join(cfg.arm_config["LOGPATH"], filename)
    )
    file_handler.setFormatter(_json_formatter())
    return file_handler


def setup_job_log(job):
    """
    Setup logging and return the path to the logfile for redirection of external calls.

    We need to return the full logfile path but set the job.logfile to just the filename.
    Binds job context (job_id, label, devpath) into structlog contextvars so every
    subsequent log call automatically includes these fields.
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

    # Swap the file handler to the per-job log file.
    # Operate on root logger so all logging.info() calls are captured.
    logger = logging.getLogger()
    logger.setLevel(cfg.arm_config["LOGLEVEL"])
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler):
            logger.removeHandler(handler)

    logger.addHandler(_create_file_handler(log_file))

    # Bind job context into structlog contextvars — all subsequent log calls
    # from any module will include these fields automatically
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        job_id=job.job_id,
        label=job.label,
        devpath=job.devpath,
    )

    # These stop apprise and others spitting our secret keys if users post log online
    logging.getLogger("apprise").setLevel(logging.WARN)
    logging.getLogger("requests").setLevel(logging.WARN)
    logging.getLogger("urllib3").setLevel(logging.WARN)

    # Return the full logfile location to the logs
    return log_full


def clean_up_logs(logpath, loglife):
    """
    Delete all log files older than {loglife} days.

    If {loglife} is 0 don't delete anything.
    """
    if loglife < 1:
        logging.info("loglife is set to 0. Removal of logs is disabled")
        return False
    now = time.time()
    logging.info(f"Looking for log files older than {loglife} days old.")

    logs_folders = [logpath, os.path.join(logpath, 'progress')]
    for log_dir in logs_folders:
        logging.info(f"Checking path {log_dir} for old log files...")
        if not os.path.isdir(log_dir):
            logging.info(f"{log_dir} is not a directory or doesn't exist. Skipping.")
            continue
        for filename in os.listdir(log_dir):
            fullname = os.path.join(log_dir, filename)
            if fullname.endswith(".log") and os.stat(fullname).st_mtime < now - loglife * 86400:
                logging.info(f"Deleting log file: {filename}")
                os.remove(fullname)
    return True


def create_early_logger(stdout=True, syslog=True, file=True):
    """
    Create the root ARM logger with structured formatters.

    Configures structlog once, then sets up stdlib handlers with
    ProcessorFormatter so all existing logging calls get structured output.

    Handlers are added to BOTH the named 'ARM' logger and the root logger,
    ensuring that direct logging.info() calls (used throughout ARM) and
    named logger calls all produce structured output.
    """
    _configure_structlog()

    arm_logger = logging.getLogger("ARM")
    arm_logger.setLevel(cfg.arm_config["LOGLEVEL"])

    root_logger = logging.getLogger()
    root_logger.setLevel(cfg.arm_config["LOGLEVEL"])

    if file:
        handler = _create_file_handler("arm.log")
        arm_logger.addHandler(handler)
        root_logger.addHandler(handler)

    if syslog:
        try:
            syslog_handler = logging.handlers.SysLogHandler(address='/dev/log')
            syslog_handler.setFormatter(_syslog_formatter())
            arm_logger.addHandler(syslog_handler)
            root_logger.addHandler(syslog_handler)
        except OSError:
            # /dev/log may not exist in Docker or test environments
            pass

    if stdout:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(_console_formatter())
        arm_logger.addHandler(stream_handler)
        root_logger.addHandler(stream_handler)

    return arm_logger
