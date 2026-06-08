"""Path-confinement helpers to defend against path traversal.

These functions route user-controlled path components through
``os.path.realpath`` and a strict containment check. This is the
sanitizer pattern static analysers (e.g. CodeQL ``py/path-injection``)
recognise: untrusted input is joined onto a *trusted* base directory and
the resolved result is proven to stay inside that base before it is used
for any filesystem operation.

Always use the RETURNED value for the actual fs call — never the raw
user input — otherwise the confinement is bypassed.
"""
import os


def safe_join(base, *user_parts):
    """Join user-controlled parts onto a trusted base dir and guarantee the
    result stays inside base. Raises ValueError on traversal/escape.

    Returns the validated absolute path.
    """
    base_real = os.path.realpath(base)
    target = os.path.realpath(os.path.join(base_real, *[str(p) for p in user_parts]))
    if target != base_real and not target.startswith(base_real + os.sep):
        raise ValueError(
            f"unsafe path: {os.path.join(*[str(p) for p in user_parts])!r} "
            f"escapes {base_real!r}"
        )
    return target


def is_within(base, candidate):
    """True if candidate path is inside base (after realpath)."""
    base_real = os.path.realpath(base)
    cand_real = os.path.realpath(candidate)
    return cand_real == base_real or cand_real.startswith(base_real + os.sep)
