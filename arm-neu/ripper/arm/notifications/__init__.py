"""Notifications module — public surface only.

The rest of arm-neu must not import from this module's internals.
Only ``publish_event`` (the producer entry point) and ``router`` (the
FastAPI router) are part of the public API.
"""
from arm.notifications.events import publish_event  # noqa: F401

# router is exported by arm.notifications.api once that module exists
# (added in a later task).

__all__ = ["publish_event"]
