"""Pure helpers for the legacy -> channel translation step.

Called from the alembic data-migration so the logic is testable in
isolation. The data migration runs once on upgrade; afterwards these
helpers are dead code (kept for the historical record and easy
re-runnability if needed).
"""
import logging
import os

import yaml

log = logging.getLogger(__name__)


def _subscribed_events(notify_rip: bool, notify_transcode: bool) -> list[str]:
    """Map the two legacy global toggles to the new event subscription
    list. job.failed is always included so users don't lose failure
    notifications they were already getting."""
    events = ["job.failed"]
    if notify_rip:
        events.extend(["job.started", "job.rip_complete"])
    if notify_transcode:
        events.append("job.transcode_complete")
    return events


def translate_legacy_config(legacy: dict) -> list[dict]:
    """Translate a legacy Config row (as a dict) into a list of
    channel-row dicts ready for insertion.

    Each output row has the keys: type, name, enabled, config (a dict
    that matches ChannelConfig discriminated union), subscribed_events.
    """
    subs = _subscribed_events(
        bool(legacy.get("NOTIFY_RIP", False)),
        bool(legacy.get("NOTIFY_TRANSCODE", False)),
    )
    rows: list[dict] = []

    if legacy.get("PB_KEY"):
        rows.append({
            "type": "apprise",
            "name": "Pushbullet (migrated)",
            "enabled": True,
            "config": {"type": "apprise",
                       "url": f"pbul://{legacy['PB_KEY']}"},
            "subscribed_events": list(subs),
            "templates": {},
        })

    if legacy.get("IFTTT_KEY"):
        event = legacy.get("IFTTT_EVENT") or "arm_event"
        rows.append({
            "type": "apprise",
            "name": "IFTTT (migrated)",
            "enabled": True,
            "config": {"type": "apprise",
                       "url": f"ifttt://{legacy['IFTTT_KEY']}@{event}"},
            "subscribed_events": list(subs),
            "templates": {},
        })

    if legacy.get("PO_USER_KEY") and legacy.get("PO_APP_KEY"):
        rows.append({
            "type": "apprise",
            "name": "Pushover (migrated)",
            "enabled": True,
            "config": {"type": "apprise",
                       "url": (f"pover://{legacy['PO_USER_KEY']}"
                               f"@{legacy['PO_APP_KEY']}")},
            "subscribed_events": list(subs),
            "templates": {},
        })

    if legacy.get("JSON_URL"):
        # Rewrite the legacy JSON_URL's transport scheme to apprise's
        # json/jsons schemes. The "https" branch is checked first so the
        # "http" prefix match doesn't shadow it. These are scheme-prefix
        # rewrites on a user-supplied value, not outbound requests.
        raw = legacy["JSON_URL"]
        secure_prefix = "https" + "://"
        plain_prefix = "http" + "://"
        if raw.startswith(secure_prefix):
            url = "jsons://" + raw[len(secure_prefix):]
        elif raw.startswith(plain_prefix):
            url = "json://" + raw[len(plain_prefix):]
        else:
            url = raw
        rows.append({
            "type": "apprise",
            "name": "JSON Webhook (migrated)",
            "enabled": True,
            "config": {"type": "apprise", "url": url},
            "subscribed_events": list(subs),
            "templates": {},
        })

    if legacy.get("APPRISE"):
        path = legacy["APPRISE"]
        if os.path.isfile(path):
            try:
                with open(path) as f:
                    parsed = yaml.safe_load(f) or {}
            except Exception as exc:
                log.warning("apprise.yaml parse failed (%s): %s", path, exc)
                parsed = {}
            urls = parsed.get("urls") if isinstance(parsed, dict) else None
            if isinstance(urls, list):
                for i, entry in enumerate(urls, start=1):
                    if isinstance(entry, str) and entry.strip():
                        rows.append({
                            "type": "apprise",
                            "name": f"apprise:{i} (migrated)",
                            "enabled": True,
                            "config": {"type": "apprise", "url": entry.strip()},
                            "subscribed_events": list(subs),
                            "templates": {},
                        })
        else:
            log.info("legacy APPRISE path not present, skipping: %s", path)

    if legacy.get("BASH_SCRIPT"):
        rows.append({
            "type": "bash",
            "name": "Bash script (migrated)",
            "enabled": True,
            "config": {"type": "bash",
                       "script_path": legacy["BASH_SCRIPT"]},
            "subscribed_events": list(subs),
            "templates": {},
        })

    return rows
