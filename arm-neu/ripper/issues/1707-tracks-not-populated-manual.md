# #1707 — Track list not populated before manual wait

**Upstream:** https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1707
**Priority:** Medium
**Verdict:** REAL BUG (upstream) — already fixed in our fork (track population before manual wait)

## Problem

In manual mode, the Tracks table in the UI remains empty during the wait period. Tracks only appear after the user clicks "Start". Users need to see tracks before ripping starts so they can select which to process.

## Upstream Reports

- **Reporter:** ARM v2.22.0, TrueNAS, manual mode
- Mount failures during identification (`mount` returns exit status 32, `findmnt` returns 1)
- `pydvdid` fails with `Path '' does not exist` because mountpoint is empty
- Tracks populate correctly once ripping starts

## Root Cause (Upstream)

In upstream, the code flow runs `get_track_info()` **after** the manual wait period. Users see an empty track list during the wait, defeating the purpose of manual mode.

## Our Fork's Status

**Already fixed.** Our `makemkv_mkv()` at `arm/ripper/makemkv.py:655-697` runs `get_track_info()` **before** `manual_wait()`:

```python
def makemkv_mkv(job, rawpath):
    mode = utils.get_drive_mode(job.devpath)
    get_track_info(job.drive.mdisc, job)   # tracks populated HERE
    ...
    elif mode == 'manual':
        ...
        if manual_wait(job):               # user waits HERE, tracks already in DB
```

Track enumeration via MakeMKV (`disc:N`) does not require the disc to be mounted, so the TrueNAS mount failure is irrelevant for track population.

## Affected Code

No changes needed — our fork already has the correct ordering.

## Suggested Fix

N/A — already addressed in our architecture.
