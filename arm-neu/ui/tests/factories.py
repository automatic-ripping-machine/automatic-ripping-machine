"""Test data factories for ripper-API-shaped dicts.

Builders now live in ``backend.demo.data`` (single source of truth shared with
demo mode). This module re-exports them so existing test imports keep working.
"""

from __future__ import annotations

from backend.demo.data import make_job_dict  # noqa: F401
