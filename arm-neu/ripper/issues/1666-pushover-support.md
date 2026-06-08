# #1666 — Pushover notification support

**Upstream:** https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1666
**Priority:** Low
**Verdict:** CONFIG ISSUE / DOCUMENTATION BUG — Pushover already works via arm.yaml `PO_USER_KEY`/`PO_APP_KEY`
**Related:** #1613 (MQTT support)

## Problem

User reports Pushover notifications don't work when configured in `apprise.yaml`. The commented-out fields in apprise.yaml are a dead end — no code processes them.

## Upstream Reports

- User says Pushover is commented out in `apprise.yaml`, when they uncomment and populate the fields "nothing happens"
- No logs, no error messages, no environment details
- No comments from other users or maintainers

## Root Cause

ARM has **two separate Pushover paths**, and this is the source of confusion:

**Path 1 — Direct Pushover via arm.yaml (WORKS):**
`arm/ripper/utils.py:73-74`:
```python
if cfg.arm_config["PO_USER_KEY"] != "":
    apobj.add('pover://' + str(cfg.arm_config["PO_USER_KEY"]) + "@" + str(cfg.arm_config["PO_APP_KEY"]))
```
Configured via `PO_USER_KEY` and `PO_APP_KEY` in `arm.yaml`. This is fully functional and well-tested. The UI settings page exposes these fields.

**Path 2 — Pushover via apprise.yaml (DEAD END):**
`setup/apprise.yaml:136-138`:
```yaml
## DONT NEED YET
#PUSHOVER_USER: ""
#PUSHOVER_TOKEN: ""
```
Even if uncommented, there is **no corresponding handler in `apprise_bulk.py`**. The `build_apprise_sent()` function has no `PUSHOVER_USER` or `PUSHOVER_TOKEN` key. The apprise.yaml file defines the keys but the code never constructs a `pover://` URL from them.

## Affected Code

- `setup/apprise.yaml:136-138` — dead Pushover placeholders
- `arm/ripper/apprise_bulk.py` — `build_apprise_sent()` (missing Pushover handler)
- `arm/ripper/utils.py:73-74` — working Pushover via `PO_USER_KEY`/`PO_APP_KEY`

## Suggested Fix

**Option A (recommended):** Remove the misleading commented-out keys from `setup/apprise.yaml` and add a comment pointing to `arm.yaml`:
```yaml
## Pushover: Configure PO_USER_KEY and PO_APP_KEY in arm.yaml instead.
## See https://github.com/caronc/apprise/wiki/Notify_pushover
```

**Option B:** Add Pushover to `apprise_bulk.py`'s `build_apprise_sent()` — but this is unnecessary since the primary path already works. The `apprise.yaml` / `apprise_bulk.py` approach is a legacy secondary system with higher maintenance burden.
