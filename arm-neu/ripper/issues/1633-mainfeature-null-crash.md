# #1633 — Main feature selection crash + no fallback

**Upstream:** https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1633
**Priority:** High
**Verdict:** REAL BUG (None crash) + FEATURE REQUEST (fallback to rip-all)
**Related:** #1697 (smarter main feature selection)

## Problem

When `MAINFEATURE: 1` is set and the main feature can't be found (no tracks in DB, or the query returns None), `rip_mainfeature(job, None, rawpath)` crashes with `AttributeError`. There is no fallback to ripping all tracks.

## Upstream Reports

- User explicitly describes this as an "enhancement" — wants ARM to automatically fall back to ripping all tracks when main-feature detection fails
- The current code works as designed (rip longest track only), but lacks graceful degradation
- No logs, no error messages provided — this is a feature request backed by a real null-safety bug

## Root Cause

`arm/ripper/makemkv.py:677-680`:
```python
if job.config.MAINFEATURE:
    logging.info("Trying to find mainfeature")
    track = Track.query.filter_by(job_id=job.job_id).order_by(Track.length.desc()).first()
    rip_mainfeature(job, track, rawpath)
```

Two issues:
1. **`track` can be `None`**: If MakeMKV found titles but all tracks were filtered out or the DB query returns nothing, `track` is `None`. Then `rip_mainfeature(job, None, rawpath)` crashes at line 872 with `AttributeError: 'NoneType' object has no attribute 'track_number'`.
2. **No fallback**: If `rip_mainfeature` raises `MakeMkvRuntimeError` (title failed to rip), the entire job fails with no retry of all tracks.

## Affected Code

- `arm/ripper/makemkv.py:677-680` — main feature selection and rip call
- `arm/ripper/makemkv.py:864-872` — `rip_mainfeature()` (crashes on None track)
- `arm/ripper/makemkv.py:655-720` — `makemkv_mkv()` (the broader rip function)

## Suggested Fix

```python
# Fixed (null guard + fallback):
if job.config.MAINFEATURE:
    logging.info("Trying to find mainfeature")
    track = Track.query.filter_by(job_id=job.job_id).order_by(Track.length.desc()).first()
    if track is None:
        logging.warning("MAINFEATURE enabled but no tracks found. Falling back to all tracks.")
        # Fall through to process_single_tracks below
    else:
        rip_mainfeature(job, track, rawpath)
        return  # Exit early after main feature rip
```

The full fallback enhancement (catching `MakeMkvRuntimeError` from `rip_mainfeature` and retrying with all tracks) is a separate design decision. Combine with #1697 for smarter track selection.
