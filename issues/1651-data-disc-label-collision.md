# #1651 — Data disc with same label silently discarded

- **Upstream:** [#1651](https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1651)
- **Verdict:** REAL BUG
- **Status:** FIXED

## Problem

`rip_data()` in `arm/ripper/utils.py` has a data-loss bug: when the final `.iso` already exists at the destination, it logs at INFO ("File already exists. Not moving.") and skips the move — but still returns `success = True`. The raw directory is then deleted at the end of the function, destroying the new rip.

## Root Cause

The completed-path collision branch (line 426-432) silently skips the move but marks the job as successful. The raw path collision is already handled (timestamp suffix), but the completed `.iso` collision was not.

## Fix

When `full_final_file` already exists, append a `_<job_id>` suffix to make it unique (e.g. `MYDATA_42.iso`), log a warning, and always move the file. Removed the silent skip branch entirely.

## Tests

- `TestRipData.test_completed_iso_collision_gets_unique_suffix` — verifies that when a completed `.iso` exists, the file gets a `_<job_id>` suffix and `shutil.move` is called
- `TestRipData.test_duplicate_label_gets_unique_filename` — existing test for raw-path collision
- `TestRipData.test_unique_label_uses_plain_filename` — existing test for clean path
