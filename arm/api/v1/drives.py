"""API v1 — Drive endpoints."""
import fcntl
import glob
import logging
import os
import re
import shutil
import subprocess

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from arm.database import db
from arm.models.system_drives import SystemDrives

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["drives"])

_CDS_NAMES = {0: "NO_INFO", 1: "NO_DISC", 2: "TRAY_OPEN", 3: "NOT_READY", 4: "DISC_OK"}


@router.get('/drives/diagnostic')
async def drive_diagnostic():
    """Run udev and device diagnostics for all optical drives."""
    checks: list[dict] = []
    issues: list[str] = []

    # --- udevd running? (may be udevd or systemd-udevd) ---
    udevd_running = False
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        try:
            comm = open(f"/proc/{pid}/comm").read().strip()
            if "udevd" in comm:
                udevd_running = True
                break
        except (FileNotFoundError, IOError):
            continue
    if not udevd_running:
        issues.append("udevd is not running inside the container — disc hotplug events won't work")

    # --- kernel cdrom info ---
    kernel_drives: list[str] = []
    try:
        with open("/proc/sys/dev/cdrom/info") as f:
            for line in f:
                if line.startswith("drive name:"):
                    kernel_drives = line.split(":")[1].split()
                    break
    except FileNotFoundError:
        issues.append("/proc/sys/dev/cdrom/info not found — no optical drives visible to kernel")

    # --- per-drive checks ---
    # Collect all srN names from kernel, sysfs, and /dev
    all_devnames: set[str] = set(kernel_drives)
    for p in glob.glob("/sys/block/sr*"):
        all_devnames.add(os.path.basename(p))
    for p in glob.glob("/dev/sr*"):
        all_devnames.add(os.path.basename(p))

    for devname in sorted(all_devnames):
        dev_path = f"/dev/{devname}"
        sys_path = f"/sys/block/{devname}"
        lock_path = f"/home/arm/.arm_{devname}.lock"

        diag: dict = {"devname": devname, "status": "ok", "issues": []}

        # Device node
        diag["dev_node_exists"] = os.path.exists(dev_path)
        if not diag["dev_node_exists"]:
            diag["issues"].append(f"{dev_path} missing — device node not created")

        # sysfs
        diag["sysfs_exists"] = os.path.isdir(sys_path)
        if not diag["sysfs_exists"]:
            diag["issues"].append(f"{sys_path} missing — kernel doesn't see this drive")

        # major:minor
        diag["major_minor"] = None
        try:
            with open(f"{sys_path}/dev") as f:
                diag["major_minor"] = f.read().strip()
        except (FileNotFoundError, IOError):
            pass

        # In kernel cdrom list?
        diag["in_kernel_cdrom"] = devname in kernel_drives
        if not diag["in_kernel_cdrom"]:
            diag["issues"].append(f"{devname} not listed in /proc/sys/dev/cdrom/info")

        # ioctl tray status
        diag["tray_status"] = None
        diag["tray_status_name"] = None
        if diag["dev_node_exists"]:
            try:
                fd = os.open(dev_path, os.O_RDONLY | os.O_NONBLOCK)
                try:
                    status = fcntl.ioctl(fd, 0x5326, 0)
                    diag["tray_status"] = status
                    diag["tray_status_name"] = _CDS_NAMES.get(status, f"UNKNOWN({status})")
                except OSError as e:
                    diag["tray_status_name"] = f"ioctl failed: {e}"
                    diag["issues"].append(f"Cannot read tray status: {e}")
                finally:
                    os.close(fd)
            except OSError as e:
                diag["tray_status_name"] = f"open failed: {e}"
                diag["issues"].append(f"Cannot open {dev_path}: {e}")

        # udevadm properties
        diag["udevadm"] = {}
        try:
            result = subprocess.run(
                ["udevadm", "info", "--query=property", dev_path],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if "=" in line:
                        k, v = line.split("=", 1)
                        if k.startswith("ID_CDROM") or k in ("ID_VENDOR_ENC", "ID_MODEL_ENC", "ID_BUS", "ID_FS_TYPE", "ID_FS_LABEL"):
                            diag["udevadm"][k] = v
                if not diag["udevadm"]:
                    diag["issues"].append("udevadm returned no CDROM properties — udev database may be empty in container")
            else:
                diag["issues"].append(f"udevadm info failed: {result.stderr.strip()}")
        except FileNotFoundError:
            diag["issues"].append("udevadm not found in container")
        except subprocess.TimeoutExpired:
            diag["issues"].append("udevadm info timed out")

        # flock check
        diag["arm_processing"] = False
        if os.path.exists(lock_path):
            try:
                fd = os.open(lock_path, os.O_RDONLY)
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    fcntl.flock(fd, fcntl.LOCK_UN)
                except BlockingIOError:
                    diag["arm_processing"] = True
                finally:
                    os.close(fd)
            except OSError:
                pass

        # In database?
        db_drive = SystemDrives.query.filter(
            SystemDrives.mount.like(f"%{devname}")
        ).first()
        diag["in_database"] = db_drive is not None
        if not diag["in_database"]:
            diag["issues"].append(f"{devname} not found in ARM database — run drive rescan")

        if diag["issues"]:
            diag["status"] = "warning"

        checks.append(diag)

    if not all_devnames:
        issues.append("No optical drives found anywhere (kernel, sysfs, or /dev)")

    return {
        "success": True,
        "udevd_running": udevd_running,
        "kernel_drives": kernel_drives,
        "drives": checks,
        "issues": issues,
    }


@router.post('/drives/rescan')
async def rescan_drives():
    """Re-detect optical drives and update the database.

    Python-level only — refreshes the drive inventory in the DB
    by scanning /sys and udev. Does NOT trigger rips.
    """
    from arm.services.drives import drives_update

    try:
        before = SystemDrives.query.count()
        removed = drives_update()
        after = SystemDrives.query.count()
        log.info("Drive rescan: %d before, %d after, %d removed", before, after, removed)
        return {
            "success": True,
            "drive_count": after,
            "drives_changed": before != after,
        }
    except Exception as e:
        log.exception("Drive rescan failed")
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=500,
        )


@router.post('/drives/{drive_id}/scan')
async def scan_drive(drive_id: int):
    """Trigger a disc scan on the given drive.

    Runs rescan_drive.sh in the background, which checks for a disc
    and starts a rip if one is found.  The script's own locking
    (flock + ioctl disc-presence check) prevents duplicate runs.
    """
    drive = SystemDrives.query.get(drive_id)
    if not drive:
        return JSONResponse({"success": False, "error": "Drive not found"}, status_code=404)
    if not drive.mount:
        return JSONResponse({"success": False, "error": "Drive has no mount path"}, status_code=400)

    # mount may be /dev/sr0 or /mnt/dev/sr0 — extract just the srN part
    devname = drive.mount.rstrip("/").rsplit("/", 1)[-1]
    script = "/opt/arm/scripts/docker/rescan_drive.sh"

    try:
        subprocess.Popen(
            [script, devname],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        log.info("Scan triggered for drive %s (%s)", drive_id, devname)
        return {"success": True, "drive_id": drive_id, "devname": devname}
    except Exception as e:
        log.exception("Failed to trigger scan for drive %s", drive_id)
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=500,
        )


@router.patch('/drives/{drive_id}')
async def update_drive(drive_id: int, request: Request):
    """Update a drive's user-editable fields (name, description)."""
    drive = SystemDrives.query.get(drive_id)
    if not drive:
        return JSONResponse({"success": False, "error": "Drive not found"}, status_code=404)

    body = await request.json()
    if not body:
        return JSONResponse({"success": False, "error": "No fields to update"}, status_code=400)

    updated = {}
    if 'name' in body:
        drive.name = str(body['name']).strip()[:100]
        updated['name'] = drive.name
    if 'description' in body:
        drive.description = str(body['description']).strip()[:200]
        updated['description'] = drive.description
    if 'uhd_capable' in body:
        drive.uhd_capable = bool(body['uhd_capable'])
        updated['uhd_capable'] = drive.uhd_capable

    if not updated:
        return JSONResponse({"success": False, "error": "No valid fields provided"}, status_code=400)

    db.session.commit()
    return {"success": True, "drive_id": drive.drive_id}
