"""File browser service — browse and manage media directories."""
import logging
import os
import shutil
import stat
from datetime import datetime, timezone
from pathlib import Path

import arm.config.config as cfg
from arm.common.path_safety import is_within, safe_join

log = logging.getLogger(__name__)

# Extension → category mapping
_EXTENSION_CATEGORIES = {
    # video
    'mkv': 'video', 'mp4': 'video', 'avi': 'video', 'm4v': 'video',
    'ts': 'video', 'wmv': 'video', 'iso': 'video',
    # audio
    'flac': 'audio', 'mp3': 'audio', 'wav': 'audio', 'aac': 'audio',
    'ogg': 'audio', 'm4a': 'audio',
    # image
    'jpg': 'image', 'jpeg': 'image', 'png': 'image', 'gif': 'image',
    'bmp': 'image', 'webp': 'image',
    # text
    'txt': 'text', 'log': 'text', 'nfo': 'text', 'srt': 'text',
    'sub': 'text', 'ass': 'text',
    # archive
    'zip': 'archive', 'rar': 'archive', '7z': 'archive',
    'tar': 'archive', 'gz': 'archive',
}


def get_allowed_roots() -> dict[str, str]:
    """Return a dict of key → absolute path for all configured media roots."""
    roots = {}
    mapping = {
        'raw': 'RAW_PATH',
        'completed': 'COMPLETED_PATH',
        'transcode': 'TRANSCODE_PATH',
        'music': 'MUSIC_PATH',
        'ingress': 'INGRESS_PATH',
    }
    for key, config_key in mapping.items():
        path = cfg.arm_config.get(config_key, '')
        if path and os.path.isdir(path):
            roots[key] = str(Path(path).resolve())
    return roots


class _MountInfo:
    """Info about a single mount point."""
    __slots__ = ('source', 'readonly')

    def __init__(self, source: str, readonly: bool):
        self.source = source
        self.readonly = readonly


def _read_host_mounts() -> dict[str, _MountInfo]:
    """Parse /proc/self/mountinfo to map container paths → mount info.

    Handles Docker bind mounts (host path in field 3) and NFS mounts
    (remote path from the device field after the ``-`` separator).

    Returns a dict of container_mount_point → _MountInfo (source path + readonly flag).
    """
    mounts: dict[str, _MountInfo] = {}
    try:
        with open('/proc/self/mountinfo') as f:
            for line in f:
                parts = line.split()
                if len(parts) < 10:
                    continue
                mount_point = parts[4]
                mount_opts = parts[5]  # per-mount options (ro/rw,relatime,...)
                host_root = parts[3]  # root within the mounted filesystem
                readonly = mount_opts.startswith('ro,') or mount_opts == 'ro'

                # Locate the "-" separator to find fs-type and device
                try:
                    sep_idx = parts.index('-')
                except ValueError:
                    continue
                if sep_idx + 2 >= len(parts):
                    continue
                fs_type = parts[sep_idx + 1]
                device = parts[sep_idx + 2]

                # Docker bind mounts: host_root is the actual host path
                if host_root != '/' and fs_type not in ('proc', 'sysfs', 'tmpfs', 'devpts', 'cgroup', 'cgroup2'):
                    mounts[mount_point] = _MountInfo(host_root, readonly)
                # NFS mounts: device is "host:/remote/path"
                elif fs_type == 'nfs' and ':' in device:
                    remote_path = device.split(':', 1)[1]
                    mounts[mount_point] = _MountInfo(remote_path, readonly)
    except OSError:
        pass
    return mounts


def _find_mount_for_path(path: str, host_mounts: dict[str, _MountInfo]) -> tuple[str, _MountInfo] | tuple[str, None]:
    """Find the best (longest) matching mount point for a given path."""
    best_mount = ''
    best_info = None
    for mount_point, info in host_mounts.items():
        if (path == mount_point or path.startswith(mount_point + '/')) and len(mount_point) > len(best_mount):
            best_mount = mount_point
            best_info = info
    return best_mount, best_info


def is_path_readonly(path: str) -> bool:
    """Check if a path is on a read-only mount."""
    host_mounts = _read_host_mounts()
    _, info = _find_mount_for_path(str(Path(path).resolve()), host_mounts)
    return info.readonly if info else False


def get_roots() -> list[dict]:
    """Return list of browsable root directories with labels, host paths, and readonly status."""
    labels = {
        'raw': 'Raw',
        'completed': 'Completed',
        'transcode': 'Transcode',
        'music': 'Music',
        'ingress': 'Ingress',
    }
    host_mounts = _read_host_mounts()
    results = []
    for key, path in get_allowed_roots().items():
        entry: dict = {
            'key': key,
            'label': labels.get(key, key.title()),
            'path': path,
            'readonly': False,
        }
        mount_point, info = _find_mount_for_path(path, host_mounts)
        if info:
            suffix = path[len(mount_point):]
            entry['host_path'] = info.source + suffix
            entry['readonly'] = info.readonly
        results.append(entry)
    return results


def validate_path(path: str) -> Path:
    """Resolve and validate that a path is under an allowed root.

    :param path: User-provided path string
    :return: Resolved Path object
    :raises ValueError: if path escapes allowed roots
    :raises FileNotFoundError: if path does not exist
    """
    roots = get_allowed_roots()
    for root_path in roots.values():
        try:
            # Route the user-controlled path through the confinement helper.
            # safe_join resolves symlinks and guarantees the result stays
            # inside this allowed root; it raises ValueError otherwise.
            confined = Path(safe_join(root_path, path))
        except ValueError:
            continue
        if not confined.exists():
            raise FileNotFoundError(f"Path not found: {path}")
        return confined
    raise ValueError("Path is outside allowed media directories")


_PERM_BITS = (
    (stat.S_IRUSR, 'r'), (stat.S_IWUSR, 'w'), (stat.S_IXUSR, 'x'),
    (stat.S_IRGRP, 'r'), (stat.S_IWGRP, 'w'), (stat.S_IXGRP, 'x'),
    (stat.S_IROTH, 'r'), (stat.S_IWOTH, 'w'), (stat.S_IXOTH, 'x'),
)


def _format_permissions(mode: int) -> str:
    """Format a stat mode into a unix-style permission string like 'rwxr-xr-x'."""
    return ''.join(ch if mode & bit else '-' for bit, ch in _PERM_BITS)


def _get_owner_group(st: os.stat_result) -> tuple[str, str]:
    """Return (owner, group) names for a stat result, falling back to uid/gid."""
    import pwd
    import grp
    try:
        owner = pwd.getpwuid(st.st_uid).pw_name
    except KeyError:
        owner = str(st.st_uid)
    try:
        group = grp.getgrgid(st.st_gid).gr_name
    except KeyError:
        group = str(st.st_gid)
    return owner, group


def classify_file(name: str) -> str:
    """Return a category string based on file extension."""
    ext = name.rsplit('.', 1)[-1].lower() if '.' in name else ''
    return _EXTENSION_CATEGORIES.get(ext, 'other')


def _dir_size(path: Path) -> int:
    """Return total size of all files under *path* (recursive)."""
    total = 0
    try:
        for entry in os.scandir(path):
            if entry.is_file(follow_symlinks=False):
                total += entry.stat().st_size
            elif entry.is_dir(follow_symlinks=False):
                total += _dir_size(Path(entry.path))
    except OSError:
        pass
    return total


def _compute_parent(resolved_str, roots):
    """Return parent path or None if at a root."""
    for root_path in roots.values():
        if resolved_str != root_path and resolved_str.startswith(root_path + os.sep):
            return str(Path(resolved_str).parent)
    return None


def _classify_entry(entry_path: str) -> tuple[str, bool]:
    """Return (kind, importable) for a directory entry.

    kind is one of:
      - 'dir':   directory (importable iff it contains BDMV/ or VIDEO_TS/)
      - 'iso':   .iso disc image (always importable)
      - 'other': any other file (never importable)

    The Import wizard uses these flags to render folders + ISOs in one
    mixed listing and grey out non-importable entries.
    """
    if os.path.isdir(entry_path):
        has_bdmv = os.path.isdir(os.path.join(entry_path, "BDMV"))
        has_video_ts = os.path.isdir(os.path.join(entry_path, "VIDEO_TS"))
        return ("dir", has_bdmv or has_video_ts)
    if entry_path.lower().endswith(".iso"):
        return ("iso", True)
    return ("other", False)


def _build_entry(item, st, shallow=False):
    """Build a directory entry dict from a Path and its stat result.

    When *shallow* is True, directory sizes are reported as 0 instead of
    recursively calculated — much faster for large or NFS-backed trees.
    """
    is_dir = item.is_dir()
    owner, group = _get_owner_group(st)
    if is_dir:
        size = 0 if shallow else _dir_size(item)
    else:
        size = st.st_size
    kind, importable = _classify_entry(str(item))
    return {
        'name': item.name,
        'type': 'directory' if is_dir else 'file',
        'size': size,
        'modified': datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
        'extension': '' if is_dir else item.suffix.lstrip('.').lower(),
        'category': 'directory' if is_dir else classify_file(item.name),
        'permissions': _format_permissions(st.st_mode),
        'owner': owner,
        'group': group,
        'kind': kind,
        'importable': importable,
    }


def list_directory(path: str) -> dict:
    """List contents of a validated directory.

    :param path: Directory path to list
    :return: dict with path, parent, and entries
    :raises ValueError: if path is outside allowed roots
    :raises FileNotFoundError: if path does not exist
    :raises NotADirectoryError: if path is not a directory
    """
    resolved = validate_path(path)
    if not resolved.is_dir():
        raise NotADirectoryError(f"Not a directory: {path}")

    resolved_str = str(resolved)
    roots = get_allowed_roots()
    parent = _compute_parent(resolved_str, roots)

    # Use shallow mode (skip recursive dir sizes) for the ingress root
    # to avoid slow NFS traversal of large media libraries.
    ingress_root = roots.get('ingress', '')
    shallow = bool(ingress_root and resolved_str.startswith(ingress_root))

    entries = []
    try:
        for item in resolved.iterdir():
            try:
                # Verify the name is valid UTF-8 before building the entry —
                # NFS shares sometimes contain filenames with surrogate bytes
                # that crash JSON serialization.
                item.name.encode('utf-8')
                entries.append(_build_entry(item, item.stat(), shallow=shallow))
            except (OSError, UnicodeEncodeError) as exc:
                log.debug("Skipping inaccessible entry %s: %s", item, exc)
    except PermissionError as exc:
        log.error("Cannot list directory %s: %s", resolved, exc)
        raise

    entries.sort(key=lambda e: (0 if e['type'] == 'directory' else 1, e['name'].lower()))

    return {
        'path': resolved_str,
        'parent': parent,
        'entries': entries,
        'readonly': is_path_readonly(resolved_str),
    }


def rename_item(path: str, new_name: str) -> dict:
    """Rename a file or directory.

    :param path: Current path
    :param new_name: New name (must not contain / or ..)
    :return: dict with success and new_path
    :raises ValueError: for invalid names or paths outside roots
    """
    if '/' in new_name or '..' in new_name:
        raise ValueError("Invalid name: must not contain '/' or '..'")
    if not new_name or not new_name.strip():
        raise ValueError("Name cannot be empty")

    resolved = validate_path(path)

    # Confine the new name to the (already validated) parent directory and
    # re-check that it stays under an allowed root. safe_join rejects any
    # traversal; the explicit root check guards against the parent itself
    # sitting on a root boundary.
    new_path = Path(safe_join(str(resolved.parent), new_name))
    roots = get_allowed_roots()
    under_root = any(is_within(root_path, new_path) for root_path in roots.values())
    if not under_root:
        raise ValueError("Destination is outside allowed media directories")

    if new_path.exists():
        raise FileExistsError(f"Already exists: {new_name}")

    resolved.rename(new_path)
    log.info("Renamed %s → %s", resolved, new_path)
    return {'success': True, 'new_path': str(new_path)}


def move_item(path: str, destination: str) -> dict:
    """Move a file or directory to a new location.

    :param path: Source path
    :param destination: Destination directory path
    :return: dict with success and new_path
    :raises ValueError: if either path is outside allowed roots
    """
    source = validate_path(path)
    dest_dir = validate_path(destination)

    if not dest_dir.is_dir():
        raise NotADirectoryError(f"Destination is not a directory: {destination}")

    # Confine the moved item to the (already validated) destination dir.
    final_path = Path(safe_join(str(dest_dir), source.name))
    if final_path.exists():
        raise FileExistsError(f"Already exists at destination: {source.name}")

    shutil.move(str(source), str(final_path))
    log.info("Moved %s → %s", source, final_path)
    return {'success': True, 'new_path': str(final_path)}


def delete_item(path: str) -> dict:
    """Delete a file or directory.

    :param path: Path to delete
    :return: dict with success
    :raises ValueError: if path is a root directory or outside allowed roots
    """
    resolved = validate_path(path)

    # Never allow deleting a root directory itself
    roots = get_allowed_roots()
    for root_path in roots.values():
        if str(resolved) == root_path:
            raise ValueError("Cannot delete a root media directory")

    if resolved.is_dir():
        shutil.rmtree(resolved)
    else:
        resolved.unlink()

    log.info("Deleted %s", resolved)
    return {'success': True}


def create_directory(path: str, name: str) -> dict:
    """Create a new subdirectory.

    :param path: Parent directory path (must be under an allowed root)
    :param name: Name of the new directory
    :return: dict with success and new_path
    :raises ValueError: for invalid names or paths outside roots
    """
    if '/' in name or '..' in name:
        raise ValueError("Invalid name: must not contain '/' or '..'")
    if not name or not name.strip():
        raise ValueError("Name cannot be empty")

    parent = validate_path(path)
    if not parent.is_dir():
        raise NotADirectoryError(f"Parent is not a directory: {path}")

    # Confine the new directory to the (already validated) parent dir.
    new_dir = Path(safe_join(str(parent), name))
    if new_dir.exists():
        raise FileExistsError(f"Already exists: {name}")

    new_dir.mkdir()
    log.info("Created directory %s", new_dir)
    return {'success': True, 'new_path': str(new_dir)}


def fix_item_permissions(path: str) -> dict:
    """Fix ownership and permissions for a file or directory.

    Sets ownership to ARM_UID:ARM_GID and permissions to 775 (dirs) or 664 (files).
    For directories, applies recursively.

    :param path: Path to fix
    :return: dict with success and count of items fixed
    """
    resolved = validate_path(path)
    uid = int(os.environ.get('ARM_UID', 1000))
    gid = int(os.environ.get('ARM_GID', 1000))
    dir_mode = 0o775
    file_mode = 0o664
    fixed = 0

    if resolved.is_dir():
        for root, dirs, files in os.walk(str(resolved)):
            root_path = Path(root)
            os.chown(root, uid, gid)
            os.chmod(root, dir_mode)
            fixed += 1
            for name in files:
                fp = root_path / name
                os.chown(str(fp), uid, gid)
                os.chmod(str(fp), file_mode)
                fixed += 1
    else:
        os.chown(str(resolved), uid, gid)
        os.chmod(str(resolved), file_mode)
        fixed = 1

    log.info("Fixed permissions on %s (%d items, uid=%d, gid=%d)", resolved, fixed, uid, gid)
    return {'success': True, 'fixed': fixed}
