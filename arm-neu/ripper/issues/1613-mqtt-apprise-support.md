# #1613 — MQTT support for Apprise notifications

**Upstream:** https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1613
**Priority:** Low
**Verdict:** FEATURE REQUEST — needs `paho-mqtt` dependency and configuration surface
**Related:** #1666 (Pushover support)

## Problem

Users want MQTT notification support for home automation integration (Home Assistant, Node-RED, etc.). Apprise supports MQTT but the `paho-mqtt` dependency is not installed, no MQTT configuration exists, and no code handles MQTT URL construction.

## Upstream Reports

- User linked the Apprise MQTT wiki page (https://github.com/caronc/apprise/wiki/Notify_mqtt)
- Pure feature request — no logs or error messages
- No comments from others

## Root Cause

Three missing pieces:
1. `paho-mqtt` is not listed in `docker/base/requirements.txt` — Apprise's MQTT plugin silently fails without it
2. No MQTT entries in `setup/apprise.yaml` — no example configuration
3. No MQTT handler in `arm/ripper/apprise_bulk.py` — `build_apprise_sent()` has no MQTT entry

Even the direct URL approach in `notify()` at `utils.py:75` won't work for MQTT — it only supports `JSON_URL` which gets converted to `json://`/`jsons://`.

**Note:** The entire `apprise_bulk.py` / `apprise.yaml` system is over-engineered — every service requires manual URL construction in Python code that mirrors what Apprise already does natively. A better long-term approach would be letting users pass raw Apprise URLs directly (e.g., `mqtt://user:pass@broker/topic`).

## Affected Code

- `docker/base/requirements.txt` — needs `paho-mqtt` added
- `setup/apprise.yaml` — needs MQTT example added
- `arm/ripper/apprise_bulk.py` — needs MQTT handler in `build_apprise_sent()`

## Suggested Fix

**Minimal approach:**
1. Add `paho-mqtt` to `docker/base/requirements.txt`
2. Add commented MQTT example to `setup/apprise.yaml`:
   ```yaml
   ## MQTT
   ## Full info @ https://github.com/caronc/apprise/wiki/Notify_mqtt
   # MQTT_HOST: ""
   # MQTT_TOPIC: "arm/notifications"
   ```
3. Add MQTT handler to `apprise_bulk.py`
4. Requires base image rebuild (`publish-base-image.yml`)

**Workaround:** Users can use `BASH_SCRIPT` hook with `mosquitto_pub` to publish MQTT messages today without any ARM code changes.
