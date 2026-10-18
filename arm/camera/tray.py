#!/usr/bin/env python3
"""
Optical drive tray state polling.

Uses the ``CDROM_DRIVE_STATUS`` ioctl, the same call ``arm.models.system_drives`` makes for the
UI, but without that module's Flask/database imports.
"""
import enum
import fcntl
import glob
import logging
import os
import re
import time
from collections import namedtuple
from typing import Callable, Dict, Iterable, List, Optional

CDROM_DRIVE_STATUS = 0x5326
"""ioctl request number, see linux/include/uapi/linux/cdrom.h"""

TrayTransition = namedtuple("TrayTransition", "devname old new timestamp")
"""A change of tray state. ``timestamp`` is ``time.monotonic()`` when the change was seen."""


class TrayState(enum.IntEnum):
    """Values returned by CDROM_DRIVE_STATUS"""
    NO_INFO = 0
    NO_DISC = 1
    TRAY_OPEN = 2
    DRIVE_NOT_READY = 3
    DISC_OK = 4


def read_tray_status(devpath: str, logger=logging) -> Optional[int]:
    """
    Query the drive's tray state.

    :param devpath: ``/dev/sr0`` style path
    :return: a ``TrayState`` value or ``None`` when the drive could not be queried
    """
    try:
        handle = os.open(devpath, os.O_RDONLY | os.O_NONBLOCK)
    except OSError as error:
        logger.debug(f"Cannot open {devpath}: {error}")
        return None
    try:
        return fcntl.ioctl(handle, CDROM_DRIVE_STATUS, 0)
    except OSError as error:
        logger.debug(f"CDROM_DRIVE_STATUS failed for {devpath}: {error}")
        return None
    finally:
        os.close(handle)


def discover_drives(configured: str = "", pattern: str = "/dev/sr*") -> List[str]:
    """
    Work out which drives to watch.

    :param configured: ``CAMERA_DRIVES`` config value, comma separated kernel names (``sr0,sr1``)
                       or full paths; blank means every drive matching ``pattern``
    :return: sorted list of ``/dev/srN`` paths
    """
    drives = []
    if configured and str(configured).strip():
        for item in re.split(r"[,\s;]+", str(configured).strip()):
            if not item:
                continue
            drives.append(item if item.startswith("/dev/") else f"/dev/{item}")
    else:
        drives = [p for p in glob.glob(pattern) if re.match(r"^/dev/sr\d+$", p)]
    return sorted(set(drives))


def is_tray_close(transition: TrayTransition) -> bool:
    """True when the tray went from open to any other known state."""
    return (transition.old == TrayState.TRAY_OPEN
            and transition.new is not None
            and transition.new != TrayState.TRAY_OPEN)


class TrayWatcher:
    """
    Polls a set of drives and reports state transitions.

    ``status_fn`` is injectable so tests can drive the watcher without hardware.
    """

    def __init__(self, drives: Iterable[str],
                 status_fn: Callable[[str], Optional[int]] = read_tray_status,
                 logger=logging):
        self.drives = list(drives)
        self._status_fn = status_fn
        self._last: Dict[str, Optional[int]] = {}
        self._logger = logger

    @staticmethod
    def devname(devpath: str) -> str:
        """``/dev/sr0`` -> ``sr0``"""
        return os.path.basename(devpath)

    def poll(self, now: Optional[float] = None) -> List[TrayTransition]:
        """
        Read every drive once.

        :param now: monotonic timestamp to stamp transitions with (defaults to ``time.monotonic()``)
        :return: transitions since the previous poll; the first poll only records the baseline
        """
        now = time.monotonic() if now is None else now
        transitions = []
        for devpath in self.drives:
            state = self._status_fn(devpath)
            name = self.devname(devpath)
            if name in self._last:
                previous = self._last[name]
                if state != previous:
                    self._logger.debug(f"{name}: tray state {previous} -> {state}")
                    transitions.append(TrayTransition(name, previous, state, now))
            self._last[name] = state
        return transitions
