"""Path traversal prevention utilities."""

import os


def safe_join(base: str | os.PathLike, *user_parts: str | os.PathLike) -> str:
    """Join user-supplied parts onto a trusted base directory and guarantee
    the result stays inside that base.

    Uses os.path.realpath for both sides so symlinks are resolved before the
    containment check — the pattern recognised by CodeQL as a path-traversal
    sanitizer.

    Returns the validated absolute path string.
    Raises ValueError if the resolved target escapes base.
    """
    base_real = os.path.realpath(os.fspath(base))
    joined = os.path.join(base_real, *[os.fspath(p) for p in user_parts])
    target = os.path.realpath(joined)
    if target != base_real and not target.startswith(base_real + os.sep):
        raise ValueError(f"Path traversal: target escapes base {base_real!r}")
    return target
