# #1639 — Settings not persisting after `importlib.reload()`

- **Upstream:** [#1639](https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1639)
- **Verdict:** REAL BUG
- **Status:** FIXED

## Problem

`arm/api/v1/settings.py` calls `importlib.reload(cfg)` after writing `arm.yaml`. The reload re-executes `config.py` module-level code, creating a **new** `arm_config` dict. But other modules that imported `cfg.arm_config` at load time hold references to the **old** dict object. The new dict is orphaned — settings appear saved but don't take effect.

## Root Cause

Python's `importlib.reload()` re-executes the module and rebinds its top-level names. Any other module that did `from arm.config.config import arm_config` or even `import arm.config.config as cfg` and cached `cfg.arm_config` in a local variable still holds the old dict.

## Fix

Instead of `importlib.reload()`, mutate the existing dict in-place:
1. Re-read the YAML from disk with `yaml.safe_load()`
2. `cfg.arm_config.clear()` + `cfg.arm_config.update(new_values)`
3. This preserves all existing references to `cfg.arm_config`

Removed the `import importlib` since it's no longer needed.

## Tests

- `TestSettingsReload.test_reload_updates_existing_reference` — grabs a reference to `cfg.arm_config` before the update, verifies the same dict object contains new values after
