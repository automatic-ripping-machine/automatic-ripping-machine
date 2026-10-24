"""Load or create the Flask SECRET_KEY used to sign session cookies"""
import logging
import os
import secrets
import time

log = logging.getLogger(__name__)

SECRET_KEY_ENV = "ARM_SECRET_KEY"
SECRET_KEY_FILENAME = ".flask_secret_key"


def _read_key(path):
    """Read the key file, waiting briefly in case another process is still writing it"""
    for _ in range(10):
        with open(path, encoding="utf-8") as key_file:
            key = key_file.read().strip()
        if key:
            return key
        time.sleep(0.1)
    return None


def _create_key(path):
    """Atomically create the key file (mode 0600); return None if it already exists"""
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return None
    key = secrets.token_hex(32)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as key_file:
            key_file.write(key)
    except OSError:
        # Don't leave an empty key file behind for the next start
        os.unlink(path)
        raise
    log.info(f"Generated new Flask secret key in {path}")
    return key


def load_secret_key(key_dir):
    """
    Return the secret key for signing Flask session cookies.

    The ARM_SECRET_KEY environment variable wins if set. Otherwise the key is
    read from (or generated into) a file in key_dir, so it is shared by the UI and
    the ripper and survives restarts. If that fails, a random in-memory key is used.
    """
    env_key = os.environ.get(SECRET_KEY_ENV)
    if env_key:
        return env_key

    path = os.path.join(key_dir, SECRET_KEY_FILENAME)
    try:
        key = _create_key(path) or _read_key(path)
        if key:
            return key
        log.warning(f"Flask secret key file {path} is empty")
    except OSError as error:
        log.warning(f"Could not read or create Flask secret key file {path}: {error}")
    log.warning("Using a temporary secret key - logins will not survive a restart of ARM. "
                f"Make {key_dir} writable or set the ARM_SECRET_KEY environment variable.")
    return secrets.token_hex(32)
