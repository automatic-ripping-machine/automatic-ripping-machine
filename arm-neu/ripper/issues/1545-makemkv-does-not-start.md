# #1545 — MakeMKV does not start

**Upstream:** https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1545
**Priority:** High (downgraded: environmental, not ARM code)
**Verdict:** ENVIRONMENTAL (MakeMKV 1.18.x regression) + minor REAL BUG (`:d` format on None)
**Related:** #1539 (stuck at info status)

## Problem

MakeMKV's `disc:9999` scan runs during drive discovery but never transitions to actual ripping. The process hangs at the version/SDF download message and never produces drive info lines.

## Upstream Reports

- **Multiple users:** MakeMKV 1.18.1 and 1.18.2 hang during `makemkvcon --robot info disc:9999`
- MakeMKV 1.17.6/1.17.7 work correctly for the same users and hardware
- DVDs sometimes work while Blu-rays do not; appears drive-model-dependent
- MakeMKV forum thread (viewtopic.php?f=3&t=37670) confirms this is a **known MakeMKV regression** affecting Linux, drive-model-dependent (Pioneer BDR-212V fails, LG WH16NS40 works)
- **Workaround:** Downgrading MakeMKV to 1.17.6 in the base image

Key logs:
```
DEBUG ARM: makemkv.run command: '/usr/local/bin/makemkvcon --robot --messages=-stdout info --cache=1 disc:9999'
DEBUG ARM: makemkv.run MSG:1005,0,1,"MakeMKV v1.18.1 linux(x64-release) started"
DEBUG ARM: makemkv.run MSG:3338,0,2,"Downloading latest SDF to /home/arm/.MakeMKV ..."
[hangs indefinitely]
```

## Root Cause

**Primary issue (environmental):** This is a MakeMKV upstream bug in versions 1.18.x that causes `makemkvcon info disc:9999` to hang on certain drive models. Not an ARM code bug. Our fork ships MakeMKV 1.18.3 (pinned in `docker/base/VERSION_MAKEMKV`) which may be affected on certain hardware.

**Secondary issue (code bug):** If the DB is locked when storing `mdisc`, the value stays `None`, and then `arm/ripper/makemkv.py:845`:
```python
logging.info(f"MakeMKV disc number: {job.drive.mdisc:d}")
```
crashes with `TypeError` because `:d` format cannot format `None`. Our code guards against `job.drive` being None (ValueError at line 844), but `job.drive.mdisc` being None after a failed commit could still crash.

## Affected Code

- `arm/ripper/makemkv.py:822-845` — drive discovery (`disc:9999` scan)
- `arm/ripper/makemkv.py:845` — `:d` format specifier on potentially-None `mdisc`
- `arm/ripper/makemkv.py:1259-1303` — `run()` subprocess management (no timeout)

## Suggested Fix

1. **For the MakeMKV hang:** No ARM code change needed. This is a MakeMKV upstream bug. The subprocess timeout fix from #1539 would serve as a workaround (kill the hung process after a configurable timeout)
2. **For the `:d` format bug** at line 845:
   ```python
   # Add null guard before the format specifier
   if job.drive.mdisc is None:
       raise ValueError(f"mdisc is None for device {job.devpath}")
   logging.info(f"MakeMKV disc number: {job.drive.mdisc:d}")
   ```
3. Monitor MakeMKV releases — newer versions may fix the regression
