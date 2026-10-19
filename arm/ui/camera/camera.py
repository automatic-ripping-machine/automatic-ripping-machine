"""
ARM route blueprint for the disc camera setup page
Covers
- camera [GET]
- camera/save [POST]
- camera/status [JSON GET]
- camera/photos [JSON GET]
- camera/capture [POST]
- camera/preview.jpg [GET]
- camera/preview/keepalive [GET/POST]
- camera/photo [GET]

The camera daemon (arm/camera/daemon.py) is a separate process that never imports the Flask
app, so everything here goes through files in DISC_PHOTO_PATH: the daemon writes a status
file and preview frames, the UI drops marker files to ask for previews and test captures.
"""
import glob
import importlib
import json
import os
import re
import time
from pathlib import Path

from flask import Blueprint, render_template, request, session, send_file, abort, jsonify, flash, redirect, \
    url_for, make_response
from flask_login import login_required

import arm.ui.utils as ui_utils
from arm.ui import app
import arm.config.config as cfg
from arm.ui.forms import CameraSettingsForm
from arm.ripper import disc_photo

route_camera = Blueprint('route_camera', __name__,
                         template_folder='templates',
                         static_folder='../static')

# File names shared with arm/camera/daemon.py (kept in sync by hand; the daemon must not be imported here
# because it puts its own folder on sys.path).
STATUS_FILE = ".camera_status.json"
PREVIEW_REQUEST_FILE = ".preview_requested"
PREVIEW_FILE = ".preview.jpg"
CAPTURE_TRIGGER_PREFIX = ".capture_"

STALE_STATUS_SECONDS = 5.0
"""The daemon rewrites its status every second; older than this and it is not running."""
STALE_IDLE_STATUS_SECONDS = 90.0
"""A daemon with CAMERA_ENABLED false rewrites its status about once a minute, not once a second."""
STALE_PREVIEW_SECONDS = 15.0
"""Preview frames older than this are not shown so a frozen frame is never mistaken for live video."""
GALLERY_SIZE = 12

CAMERA_KEYS = ("CAMERA_ENABLED", "CAMERA_DEVICE", "CAMERA_DRIVES", "CAMERA_DRIVE_REGIONS", "CAMERA_FPS",
               "CAMERA_BUFFER_SECONDS", "CAMERA_LEAD_SECONDS", "CAMERA_JPEG_QUALITY", "DISC_PHOTO_PATH",
               "DISC_PHOTO_MAX_AGE", "DISC_PHOTO_RETENTION_DAYS", "DISC_PHOTO_OCR", "DISC_PHOTO_COPY")
"""The only arm.yaml keys the camera page is allowed to change."""
BOOL_KEYS = ("CAMERA_ENABLED", "DISC_PHOTO_OCR", "DISC_PHOTO_COPY")
INT_KEYS = {"CAMERA_FPS": (1, 60), "CAMERA_JPEG_QUALITY": (1, 100),
            "DISC_PHOTO_MAX_AGE": (0, None), "DISC_PHOTO_RETENTION_DAYS": (0, None)}
FLOAT_KEYS = {"CAMERA_BUFFER_SECONDS": (0.5, None), "CAMERA_LEAD_SECONDS": (0, None)}

DRIVE_RE = re.compile(r"^sr\d+$")
REGION_ENTRY_RE = re.compile(r"^(sr\d+):(\d+),(\d+),(\d+),(\d+)$")


def as_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "on", "y")


def photo_dir():
    """``DISC_PHOTO_PATH`` as a Path, or ``None`` when it is not configured."""
    path = cfg.arm_config.get('DISC_PHOTO_PATH', '')
    return Path(path) if path else None


def parse_regions(value):
    """``sr0:x,y,w,h;sr1:...`` -> ``{"sr0": [x, y, w, h]}``; malformed entries are dropped."""
    regions = {}
    for entry in str(value or "").split(";"):
        match = REGION_ENTRY_RE.match(entry.strip())
        if match:
            regions[match.group(1)] = [int(match.group(i)) for i in range(2, 6)]
    return regions


def format_regions(regions) -> str:
    return ";".join(f"{name}:{x},{y},{w},{h}" for name, (x, y, w, h) in sorted(regions.items()))


def parse_drives(value):
    """``CAMERA_DRIVES`` (``sr0, /dev/sr1``) -> ``["sr0", "sr1"]``. Raises ValueError on anything else."""
    drives = []
    for item in re.split(r"[,\s;]+", str(value or "").strip()):
        if not item:
            continue
        name = os.path.basename(item)
        if not DRIVE_RE.match(name):
            raise ValueError(f"'{item}' is not an optical drive name like sr0")
        if name not in drives:
            drives.append(name)
    return drives


def configured_drives():
    """Drives the daemon would watch with the current config: CAMERA_DRIVES, else every /dev/sr*."""
    try:
        drives = parse_drives(cfg.arm_config.get('CAMERA_DRIVES', ''))
    except ValueError:
        drives = []
    if not drives:
        drives = sorted(os.path.basename(p) for p in glob.glob("/dev/sr*") if DRIVE_RE.match(os.path.basename(p)))
    return drives


def read_status():
    """
    The daemon's status file plus ``found``/``stale``/``age_seconds`` so the page can tell
    "daemon not running" from "running but CAMERA_ENABLED is false".
    """
    status = {"running": False, "found": False, "stale": True, "age_seconds": None,
              "enabled": as_bool(cfg.arm_config.get('CAMERA_ENABLED', False)), "drives": []}
    folder = photo_dir()
    if folder is None:
        return status
    path = folder / STATUS_FILE
    try:
        with open(path, "r") as handle:
            data = json.load(handle)
        age = max(0.0, time.time() - os.stat(path).st_mtime)
    except (OSError, ValueError) as error:
        app.logger.debug(f"Camera status file not readable: {error}")
        return status
    if isinstance(data, dict):
        status.update(data)
    status["found"] = True
    status["age_seconds"] = round(age, 1)
    stale_after = STALE_STATUS_SECONDS if status.get("enabled") else STALE_IDLE_STATUS_SECONDS
    status["stale"] = age > stale_after
    if status["stale"]:
        status["running"] = False
    return status


def list_photos(limit=GALLERY_SIZE):
    """Newest disc photos in DISC_PHOTO_PATH with drive, capture time and size."""
    folder = photo_dir()
    if folder is None or not folder.is_dir():
        return []
    found = []
    for entry in os.scandir(folder):
        if not entry.is_file() or disc_photo.photo_devname(entry.name) is None:
            continue
        try:
            info = entry.stat()
        except OSError:
            continue
        found.append((info.st_mtime, entry.name, info.st_size))
    found.sort(reverse=True)
    photos = []
    for mtime, name, size in found[:limit]:
        taken = disc_photo.photo_timestamp(name)
        photos.append({
            "name": name,
            "drive": disc_photo.photo_devname(name),
            "taken": taken.strftime(cfg.arm_config.get('DATE_FORMAT', '%Y-%m-%d %H:%M:%S')) if taken else "",
            "age_seconds": int(max(0.0, time.time() - mtime)),
            "size_kb": round(size / 1024.0, 1),
        })
    return photos


def help_texts():
    """comments.json text for each camera key, with the YAML comment markers stripped."""
    comments = ui_utils.generate_comments()
    texts = {}
    for key in CAMERA_KEYS:
        lines = str(comments.get(key, "")).splitlines()
        texts[key] = " ".join(line.lstrip("#").strip() for line in lines if line.strip("# ").strip())
    return texts


def touch_marker(name):
    """Create/refresh a marker file in DISC_PHOTO_PATH. Returns an error message or None."""
    folder = photo_dir()
    if folder is None:
        return "DISC_PHOTO_PATH is not set"
    try:
        folder.mkdir(parents=True, exist_ok=True)
        (folder / name).touch()
    except OSError as error:
        app.logger.error(f"Cannot write {name} in {folder}: {error}")
        return f"Cannot write to {folder}: {error}"
    return None


def no_cache(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@route_camera.route('/camera')
@login_required
def camera():
    """
    Page - camera
    Method - GET
    Overview - Set up the disc camera: check the daemon, see the live preview, draw the crop
    region for each drive, tune the timing and take test photos.
    """
    status = read_status()
    values = {key: cfg.arm_config.get(key, '') for key in CAMERA_KEYS}
    drives = list(status.get("drives") or []) or configured_drives()
    session["page_title"] = "Disc Camera"
    return render_template("camera/camera.html",
                           form=CameraSettingsForm(),
                           status=status,
                           values=values,
                           bool_values={key: as_bool(values[key]) for key in BOOL_KEYS},
                           drives=drives,
                           regions=parse_regions(values["CAMERA_DRIVE_REGIONS"]),
                           help=help_texts(),
                           photos=list_photos(),
                           photo_dir=str(photo_dir() or ""),
                           read_only=not os.access(cfg.arm_config_path, os.W_OK))


def _validate_numbers(form_data, values, errors):
    for key, (low, high) in INT_KEYS.items():
        raw = str(form_data.get(key, "")).strip()
        try:
            number = int(raw)
        except ValueError:
            errors.append(f"{key} must be a whole number")
            continue
        if number < low or (high is not None and number > high):
            errors.append(f"{key} must be between {low} and {high if high is not None else 'anything'}")
        values[key] = str(number)
    for key, (low, high) in FLOAT_KEYS.items():
        raw = str(form_data.get(key, "")).strip()
        try:
            number = float(raw)
        except ValueError:
            errors.append(f"{key} must be a number")
            continue
        if number < low or (high is not None and number > high):
            errors.append(f"{key} must be at least {low}")
        values[key] = raw
    if "CAMERA_LEAD_SECONDS" in values and "CAMERA_BUFFER_SECONDS" in values \
            and float(values["CAMERA_LEAD_SECONDS"]) > float(values["CAMERA_BUFFER_SECONDS"]):
        errors.append("CAMERA_LEAD_SECONDS cannot be larger than CAMERA_BUFFER_SECONDS")


def _validate_strings(form_data, values, errors):
    try:
        values["CAMERA_DRIVES"] = ",".join(parse_drives(form_data.get("CAMERA_DRIVES", "")))
    except ValueError as error:
        errors.append(f"CAMERA_DRIVES: {error}")
    raw_regions = str(form_data.get("CAMERA_DRIVE_REGIONS", "")).strip()
    regions = parse_regions(raw_regions)
    if raw_regions and len(regions) != len([e for e in raw_regions.split(";") if e.strip()]):
        errors.append("CAMERA_DRIVE_REGIONS must look like sr0:x,y,w,h;sr1:x,y,w,h")
    values["CAMERA_DRIVE_REGIONS"] = format_regions(regions)
    for key in ("CAMERA_DEVICE", "DISC_PHOTO_PATH"):
        values[key] = str(form_data.get(key, "")).strip()
        if not values[key]:
            errors.append(f"{key} cannot be blank")


def validate_camera_form(form_data):
    """
    Turn the posted camera settings into the strings build_arm_cfg expects.

    :return: (values, errors) where values maps each CAMERA_KEY to a string and errors is a list of messages
    """
    values = {}
    errors = []
    for key in BOOL_KEYS:
        values[key] = "true" if as_bool(form_data.get(key, "")) else "false"
    _validate_numbers(form_data, values, errors)
    _validate_strings(form_data, values, errors)
    return values, errors


@route_camera.route('/camera/save', methods=['POST'])
@login_required
def camera_save():
    """
    Page - camera/save
    Method - POST
    Overview - Write the camera keys back to arm.yaml. Every other key keeps its current value,
    so the file is rebuilt the same way /save_settings does (comments included). Not a user page.
    """
    form = CameraSettingsForm()
    if not form.validate_on_submit():
        problems = "; ".join(f"{field}: {', '.join(msgs)}" for field, msgs in form.errors.items()) or "invalid form"
        flash(f"Camera settings not saved: {problems}", "danger")
        return redirect(url_for('route_camera.camera'))
    values, errors = validate_camera_form(request.form)
    if errors:
        flash("Camera settings not saved: " + "; ".join(errors), "danger")
        return redirect(url_for('route_camera.camera'))
    # arm/config/config.py stringifies every value the same way before it rewrites the file
    merged = {key: str(value) for key, value in cfg.arm_config.items()}
    merged.update(values)
    arm_cfg = ui_utils.build_arm_cfg(merged, ui_utils.generate_comments())
    try:
        with open(cfg.arm_config_path, "w") as settings_file:
            settings_file.write(arm_cfg)
    except OSError as error:
        app.logger.error(f"{cfg.arm_config_path} is read-only", exc_info=error)
        flash(f"Camera settings not saved: {cfg.arm_config_path} is not writable", "danger")
        return redirect(url_for('route_camera.camera'))
    importlib.reload(cfg)
    app.logger.info("Disc camera settings saved: " + ", ".join(f"{k}={values[k]}" for k in CAMERA_KEYS))
    flash("Camera settings saved. The camera daemon picks them up within a few seconds.", "success")
    return redirect(url_for('route_camera.camera'))


@route_camera.route('/camera/status')
@login_required
def camera_status():
    """JSON: the daemon status file, or running=false when there is none."""
    return no_cache(jsonify(read_status()))


@route_camera.route('/camera/photos')
@login_required
def camera_photos():
    """JSON: the newest disc photos for the gallery."""
    return no_cache(jsonify({"photos": list_photos()}))


@route_camera.route('/camera/capture', methods=['POST'])
@login_required
def camera_capture():
    """Ask the daemon for a test photo of one drive, exactly as if its tray had just closed."""
    drive = str(request.args.get('drive') or request.form.get('drive') or "")
    if not DRIVE_RE.match(drive):
        return jsonify({"success": False, "error": "drive must be sr0, sr1, ..."}), 400
    error = touch_marker(f"{CAPTURE_TRIGGER_PREFIX}{drive}")
    if error:
        return jsonify({"success": False, "error": error}), 500
    status = read_status()
    warning = None if status.get("running") else "The camera daemon is not running, so nothing will be captured"
    return jsonify({"success": True, "drive": drive, "warning": warning})


@route_camera.route('/camera/preview/keepalive', methods=['GET', 'POST'])
@login_required
def camera_preview_keepalive():
    """Tell the daemon the setup page is open so it keeps writing preview frames."""
    error = touch_marker(PREVIEW_REQUEST_FILE)
    if error:
        return no_cache(jsonify({"success": False, "error": error})), 500
    return no_cache(jsonify({"success": True}))


@route_camera.route('/camera/preview.jpg')
@login_required
def camera_preview():
    """The latest preview frame, or a placeholder when the daemon has not written one recently."""
    folder = photo_dir()
    preview = folder / PREVIEW_FILE if folder else None
    try:
        fresh = preview is not None and time.time() - os.stat(preview).st_mtime <= STALE_PREVIEW_SECONDS
    except OSError:
        fresh = False
    if fresh:
        response = make_response(send_file(str(preview), mimetype='image/jpeg', max_age=0))
        response.headers["X-ARM-Preview"] = "live"
    else:
        placeholder = os.path.join(app.static_folder, "img", "camera_placeholder.png")
        response = make_response(send_file(placeholder, mimetype='image/png', max_age=0))
        response.headers["X-ARM-Preview"] = "placeholder"
    return no_cache(response)


@route_camera.route('/camera/photo')
@login_required
def camera_photo():
    """
    Serve one disc photo by file name.

    Only names of the form srN_YYYYmmdd-HHMMSS.jpg are accepted and the resolved path must stay
    inside DISC_PHOTO_PATH (same rules as /discphoto).
    """
    name = os.path.basename(str(request.args.get('name') or ""))
    folder = photo_dir()
    if folder is None or not disc_photo.PHOTO_FILENAME_RE.match(name):
        abort(404)
    base = folder.resolve()
    photo = (base / name).resolve()
    if base not in photo.parents or not photo.is_file():
        abort(404)
    return send_file(str(photo), mimetype='image/jpeg', max_age=3600)
