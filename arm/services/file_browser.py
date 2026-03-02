"""File browser service — browse and manage media directories."""
import logging
import os
import shutil
import stat
from datetime import datetime, timezone
from pathlib import Path

import arm.config.config as cfg

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
    }
    for key, config_key in mapping.items():
        path = cfg.arm_config.get(config_key, '')
        if path and os.path.isdir(path):
            roots[key] = str(Path(path).resolve())
    return roots


def _read_host_mounts() -> dict[str, str]:
    """Parse /proc/self/mountinfo to map container paths → host paths.

    Returns a dict of container_mount_point → host_source_path for bind mounts.
    """
    mounts: dict[str, str] = {}
    try:
        with open('/proc/self/mountinfo') as f:
            for line in f:
                parts = line.split()
                if len(parts) < 10:
                    continue
                mount_point = parts[4]
                # The host source is field 3 (root within the filesystem)
                host_root = parts[3]
                # Skip non-bind-mount entries (overlay root, proc, sys, etc.)
                if host_root == '/' and mount_point == '/':
                    continue
                if host_root != '/':
                    mounts[mount_point] = host_root
    except OSError:
        pass
    return mounts


def get_roots() -> list[dict[str, str]]:
    """Return list of browsable root directories with labels and host paths."""
    labels = {
        'raw': 'Raw',
        'completed': 'Completed',
        'transcode': 'Transcode',
        'music': 'Music',
    }
    host_mounts = _read_host_mounts()
    results = []
    for key, path in get_allowed_roots().items():
        entry: dict[str, str] = {
            'key': key,
            'label': labels.get(key, key.title()),
            'path': path,
        }
        # Find the best matching mount for this path
        best_mount = ''
        for mount_point in host_mounts:
            if (path == mount_point or path.startswith(mount_point + '/')) and len(mount_point) > len(best_mount):
                best_mount = mount_point
        if best_mount:
            host_base = host_mounts[best_mount]
            suffix = path[len(best_mount):]
            entry['host_path'] = host_base + suffix
        results.append(entry)
    return results


def validate_path(path: str) -> Path:
    """Resolve and validate that a path is under an allowed root.

    :param path: User-provided path string
    :return: Resolved Path object
    :raises ValueError: if path escapes allowed roots
    :raises FileNotFoundError: if path does not exist
    """
    resolved = Path(path).resolve()
    roots = get_allowed_roots()
    for root_path in roots.values():
        if str(resolved) == root_path or str(resolved).startswith(root_path + os.sep):
            if not resolved.exists():
                raise FileNotFoundError(f"Path not found: {path}")
            return resolved
    raise ValueError("Path is outside allowed media directories")


def _format_permissions(mode: int) -> str:
    """Format a stat mode into a unix-style permission string like 'rwxr-xr-x'."""
    parts = []
    for who in (stat.S_IRUSR, stat.S_IWUSR, stat.S_IXUSR,
                stat.S_IRGRP, stat.S_IWGRP, stat.S_IXGRP,
                stat.S_IROTH, stat.S_IWOTH, stat.S_IXOTH):
        parts.append('r' if who in (stat.S_IRUSR, stat.S_IRGRP, stat.S_IROTH) and mode & who else
                     'w' if who in (stat.S_IWUSR, stat.S_IWGRP, stat.S_IWOTH) and mode & who else
                     'x' if who in (stat.S_IXUSR, stat.S_IXGRP, stat.S_IXOTH) and mode & who else
                     '-')
    return ''.join(parts)


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

    # Compute parent (None if at a root)
    parent = None
    roots = get_allowed_roots()
    resolved_str = str(resolved)
    for root_path in roots.values():
        if resolved_str != root_path and resolved_str.startswith(root_path + os.sep):
            parent = str(resolved.parent)
            break

    entries = []
    try:
        for item in resolved.iterdir():
            try:
                st = item.stat()
                owner, group = _get_owner_group(st)
                entry = {
                    'name': item.name,
                    'type': 'directory' if item.is_dir() else 'file',
                    'size': st.st_size if item.is_file() else 0,
                    'modified': datetime.fromtimestamp(
                        st.st_mtime, tz=timezone.utc
                    ).isoformat(),
                    'extension': item.suffix.lstrip('.').lower() if item.is_file() else '',
                    'category': 'directory' if item.is_dir() else classify_file(item.name),
                    'permissions': _format_permissions(st.st_mode),
                    'owner': owner,
                    'group': group,
                }
                entries.append(entry)
            except (PermissionError, OSError) as exc:
                log.debug("Skipping inaccessible entry %s: %s", item, exc)
    except PermissionError as exc:
        log.error("Cannot list directory %s: %s", resolved, exc)
        raise

    # Sort: directories first, then files, both alphabetically
    entries.sort(key=lambda e: (0 if e['type'] == 'directory' else 1, e['name'].lower()))

    return {
        'path': resolved_str,
        'parent': parent,
        'entries': entries,
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
    new_path = resolved.parent / new_name

    # Ensure destination is still under an allowed root
    new_resolved = new_path.resolve()
    roots = get_allowed_roots()
    under_root = False
    for root_path in roots.values():
        if str(new_resolved).startswith(root_path + os.sep) or str(new_resolved) == root_path:
            under_root = True
            break
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

    final_path = dest_dir / source.name
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

    new_dir = parent / name
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
