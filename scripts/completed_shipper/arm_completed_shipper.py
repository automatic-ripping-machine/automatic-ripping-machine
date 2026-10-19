#!/usr/bin/env python3
"""
ARM completed-rip shipper.

A sidecar for Automatic Ripping Machine (ARM) that moves finished rips from a
ripping box to a media box with rsync.  It runs from a systemd timer, outside
ARM itself, and never touches a job folder until ARM's database says the job
finished successfully.

Priority rules:

* ``COMPLETED_PATH/movies`` and ``COMPLETED_PATH/tv`` are shipped first, to the
  Plex library folders on the media box.
* ``COMPLETED_PATH/unidentified`` is shipped afterwards, one job folder at a
  time, to a separate staging folder and with its own ``--bwlimit``.  Before
  each unidentified folder the recognized folders are re-checked, so a freshly
  finished movie never waits behind more than one unidentified folder.
* An unidentified transfer never starts while a recognized folder is pending,
  including one whose rsync just failed.

Safety rules:

* Source files are removed only by ``rsync --remove-source-files`` after rsync
  exited 0, then the empty job folder is pruned.  A failed or interrupted run
  leaves the job folder in place and the next run resumes it.
* A lock file stops two runs overlapping.
* Only the standard library plus ``rsync`` are needed.
"""

import argparse
import configparser
import fcntl
import logging
import os
import shlex
import sqlite3
import subprocess
import sys

RECOGNIZED = ("movies", "tv")
UNIDENTIFIED = "unidentified"
SUCCESS_STATUS = "success"
FINISHED_STATUSES = ("success", "fail")

DEFAULTS = {
    "db_path": "/home/arm/db/arm.db",
    "completed_path": "/home/arm/media/completed",
    "remote_host": "",
    "remote_movies_path": "",
    "remote_tv_path": "",
    "remote_unidentified_path": "",
    "bwlimit_recognized": "0",
    "bwlimit_unidentified": "0",
    "ssh_options": "-o BatchMode=yes",
    "rsync_path": "rsync",
    "rsync_extra_args": "",
    "rsync_timeout": "300",
    "lock_file": "/tmp/arm-completed-shipper.lock",
    "post_ship_command": "",
}

log = logging.getLogger("arm-completed-shipper")


class ShipperError(Exception):
    """Configuration or environment problem that stops the run."""


# --------------------------------------------------------------------------- config

def load_config(path, overrides=None):
    """Read the INI config file and return a dict of settings with defaults applied."""
    parser = configparser.ConfigParser()
    parser.read_dict({"shipper": DEFAULTS})
    if path:
        if not os.path.exists(path):
            raise ShipperError(f"config file not found: {path}")
        parser.read(path)
    cfg = dict(parser["shipper"])
    for key, value in (overrides or {}).items():
        if value is not None:
            cfg[key] = str(value)
    cfg["completed_path"] = os.path.realpath(cfg["completed_path"])
    for key in ("remote_movies_path", "remote_tv_path", "remote_unidentified_path"):
        if not cfg[key]:
            raise ShipperError(f"{key} must be set")
    return cfg


def remote_root_for(cfg, sub_folder):
    """Return the destination directory for one COMPLETED_PATH sub-folder."""
    return {
        "movies": cfg["remote_movies_path"],
        "tv": cfg["remote_tv_path"],
        UNIDENTIFIED: cfg["remote_unidentified_path"],
    }[sub_folder]


def bwlimit_for(cfg, sub_folder):
    """Return the rsync --bwlimit (KiB/s, 0 = unlimited) for one sub-folder."""
    key = "bwlimit_unidentified" if sub_folder == UNIDENTIFIED else "bwlimit_recognized"
    return int(cfg[key] or 0)


# --------------------------------------------------------------------------- database

def finished_job_paths(db_path, completed_path):
    """
    Return the set of job folders under COMPLETED_PATH that are safe to ship.

    A folder qualifies when at least one job with that path has status
    ``success`` and no job with that path is still unfinished.  The DB is only
    read; ARM keeps writing to it while we run.
    """
    if not os.path.exists(db_path):
        raise ShipperError(f"ARM database not found: {db_path}")
    uri = f"file:{db_path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=30)
    try:
        rows = conn.execute("SELECT path, status FROM job WHERE path IS NOT NULL AND path != ''").fetchall()
    finally:
        conn.close()

    statuses = {}
    prefix = completed_path.rstrip(os.sep) + os.sep
    for path, status in rows:
        norm = os.path.realpath(path)
        if not norm.startswith(prefix):
            continue
        statuses.setdefault(norm, set()).add(status)

    shippable = set()
    for path, seen in statuses.items():
        if SUCCESS_STATUS not in seen:
            continue
        if any(status not in FINISHED_STATUSES for status in seen):
            log.debug("skipping %s: another job on that path is still %s", path, sorted(seen))
            continue
        shippable.add(path)
    return shippable


def pending_folders(cfg, sub_folder, shippable):
    """List job folders in COMPLETED_PATH/<sub_folder> whose job finished successfully."""
    base = os.path.join(cfg["completed_path"], sub_folder)
    if not os.path.isdir(base):
        return []
    folders = []
    for name in sorted(os.listdir(base)):
        full = os.path.realpath(os.path.join(base, name))
        if not os.path.isdir(full):
            continue
        if full in shippable:
            folders.append(full)
        else:
            log.debug("not shippable yet: %s", full)
    return folders


# --------------------------------------------------------------------------- rsync

def destination(cfg, sub_folder, local_folder):
    """Build the rsync destination string for one job folder."""
    remote_dir = os.path.join(remote_root_for(cfg, sub_folder), os.path.basename(local_folder))
    if cfg["remote_host"]:
        return f"{cfg['remote_host']}:{shlex.quote(remote_dir)}/"
    return remote_dir + os.sep


def build_rsync_command(cfg, sub_folder, local_folder, dry_run=False, verbose=False):
    """Compose the full rsync argv for shipping one job folder."""
    cmd = [cfg["rsync_path"], "-a", "--partial", "--remove-source-files",
           f"--timeout={int(cfg['rsync_timeout'])}"]
    if verbose:
        cmd.append("-v")
    if dry_run:
        cmd.append("--dry-run")
    bwlimit = bwlimit_for(cfg, sub_folder)
    if bwlimit > 0:
        cmd.append(f"--bwlimit={bwlimit}")
    if cfg["remote_host"]:
        ssh = "ssh"
        if cfg["ssh_options"]:
            ssh += " " + cfg["ssh_options"]
        cmd.extend(["-e", ssh])
    if cfg["rsync_extra_args"]:
        cmd.extend(shlex.split(cfg["rsync_extra_args"]))
    cmd.append(local_folder.rstrip(os.sep) + os.sep)
    cmd.append(destination(cfg, sub_folder, local_folder))
    return cmd


def prune_empty_dirs(folder):
    """Remove `folder` and any empty sub-directories, bottom up.  Non-empty dirs are left alone."""
    for root, dirs, files in os.walk(folder, topdown=False):
        if files:
            log.warning("leaving %s in place, files remain: %s", root, files)
            continue
        try:
            os.rmdir(root)
        except OSError as err:
            log.warning("could not remove %s: %s", root, err)


def run_post_ship_command(cfg, sub_folder, local_folder):
    """Run the optional hook after a folder has shipped (e.g. to trigger a Plex scan)."""
    hook = cfg["post_ship_command"]
    if not hook:
        return
    env = dict(os.environ, SHIPPER_TYPE=sub_folder, SHIPPER_FOLDER=os.path.basename(local_folder),
               SHIPPER_DESTINATION=destination(cfg, sub_folder, local_folder))
    result = subprocess.run(["/bin/sh", "-c", hook], env=env)
    if result.returncode != 0:
        log.warning("post_ship_command exited %d for %s", result.returncode, local_folder)


def ship_folder(cfg, sub_folder, local_folder, dry_run=False, verbose=False):
    """Rsync one job folder and remove the local copy on success.  Returns True on success."""
    cmd = build_rsync_command(cfg, sub_folder, local_folder, dry_run=dry_run, verbose=verbose)
    log.info("shipping [%s] %s -> %s", sub_folder, local_folder, cmd[-1])
    log.debug("rsync argv: %s", " ".join(shlex.quote(part) for part in cmd))
    result = subprocess.run(cmd)
    if result.returncode != 0:
        log.error("rsync exited %d for %s; leaving local copy for the next run", result.returncode, local_folder)
        return False
    if dry_run:
        log.info("dry run: would remove %s", local_folder)
        return True
    prune_empty_dirs(local_folder)
    if os.path.exists(local_folder):
        log.error("rsync succeeded but %s still has content; not treating as shipped", local_folder)
        return False
    log.info("shipped and removed %s", local_folder)
    run_post_ship_command(cfg, sub_folder, local_folder)
    return True


# --------------------------------------------------------------------------- orchestration

def ship_recognized(cfg, dry_run, verbose, stats):
    """Ship every pending movies/ and tv/ folder.  Returns True when none is left pending."""
    shippable = finished_job_paths(cfg["db_path"], cfg["completed_path"])
    all_clear = True
    for sub_folder in RECOGNIZED:
        for folder in pending_folders(cfg, sub_folder, shippable):
            if ship_folder(cfg, sub_folder, folder, dry_run, verbose):
                stats["shipped"] += 1
            else:
                stats["failed"] += 1
                all_clear = False
    return all_clear


def run(cfg, dry_run=False, verbose=False):
    """One full pass.  Returns the exit code for the process."""
    stats = {"shipped": 0, "failed": 0}
    attempted_unidentified = set()
    while True:
        recognized_clear = ship_recognized(cfg, dry_run, verbose, stats)
        if dry_run:
            # Nothing moves in a dry run, so list the unidentified folders once and stop.
            shippable = finished_job_paths(cfg["db_path"], cfg["completed_path"])
            for folder in pending_folders(cfg, UNIDENTIFIED, shippable):
                ship_folder(cfg, UNIDENTIFIED, folder, dry_run, verbose)
            break
        if not recognized_clear:
            log.warning("recognized folders still pending; not starting unidentified transfers this run")
            break
        shippable = finished_job_paths(cfg["db_path"], cfg["completed_path"])
        unidentified = [f for f in pending_folders(cfg, UNIDENTIFIED, shippable)
                        if f not in attempted_unidentified]
        if not unidentified:
            break
        # One unidentified folder at a time, then loop back and re-check movies/ and tv/.
        folder = unidentified[0]
        attempted_unidentified.add(folder)
        if ship_folder(cfg, UNIDENTIFIED, folder, dry_run, verbose):
            stats["shipped"] += 1
        else:
            stats["failed"] += 1
    log.info("done: %d shipped, %d failed", stats["shipped"], stats["failed"])
    return 1 if stats["failed"] else 0


def acquire_lock(lock_file):
    """Take an exclusive flock on lock_file, or raise ShipperError if another run holds it."""
    handle = open(lock_file, "a+")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        raise ShipperError(f"another shipper run holds {lock_file}")
    return handle


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Ship finished ARM rips to a media box with rsync.")
    parser.add_argument("-c", "--config", default="/etc/arm-completed-shipper.conf",
                        help="INI config file (default: %(default)s)")
    parser.add_argument("-n", "--dry-run", action="store_true", help="show what would ship; pass --dry-run to rsync")
    parser.add_argument("-v", "--verbose", action="store_true", help="debug logging and rsync -v")
    parser.add_argument("--db-path", help="override db_path")
    parser.add_argument("--completed-path", help="override completed_path")
    parser.add_argument("--lock-file", help="override lock_file")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv if argv is not None else sys.argv[1:])
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    try:
        cfg = load_config(args.config, {"db_path": args.db_path, "completed_path": args.completed_path,
                                        "lock_file": args.lock_file})
        lock = acquire_lock(cfg["lock_file"])
    except ShipperError as err:
        log.error("%s", err)
        return 2
    try:
        return run(cfg, dry_run=args.dry_run, verbose=args.verbose)
    finally:
        lock.close()


if __name__ == "__main__":
    sys.exit(main())
