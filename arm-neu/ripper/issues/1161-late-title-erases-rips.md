# #1161 — Setting TV show title late can result in discarded/erased rips

**Upstream:** https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1161
**Priority:** High
**Verdict:** REAL BUG (data loss) — largely fixed in our fork (no file-move step), residual inconsistency in `setup_rawpath`

## Problem

When ripping multi-disc TV series and correcting the disc title after the rip has begun, the completed files are silently lost. The rip succeeds into a raw folder named after the auto-detected title, but when ARM moves files to the completed folder using the corrected (manual) title, filename collisions with a prior disc cause ARM to skip all files, then delete the raw directory.

## Upstream Reports

- **Reporter:** ARM 2.7.0, Docker, Ubuntu 20.04 — ripping Stargate SG-1 multi-disc sets
- Multiple users confirmed across later versions
- Files silently deleted when completed folder already exists from a prior disc
- No timestamped fallback folder created
- One commenter reported files overwritten in some cases

## Root Cause (Upstream)

Mismatch between what directory MakeMKV wrote to (raw folder based on `title_auto`/original title) and what directory the post-rip logic uses for "completed" destination (corrected title). When file collisions occur at the destination, the code refuses to overwrite and then deletes the raw directory.

## Our Fork's Status

**Largely fixed by architecture.** We removed the entire HandBrake/FFmpeg transcoding pipeline and the associated file-moving logic (`move_files`, `skip_transcode_movie`) that caused the data loss. The transcoder service handles file operations separately.

Additionally, `build_raw_path()` at `arm/models/job.py:355-359` uses `title_auto` (not `title_manual`), so the raw path always matches what MakeMKV created on disk.

**Residual inconsistency:** `setup_rawpath()` at `arm/ripper/makemkv.py:962` uses `job.title` instead of `job.title_auto`:
```python
raw_path = os.path.join(str(job.config.RAW_PATH), f"{job.title}_{job.stage}")
```
If the user corrects the title during manual wait before `setup_rawpath` runs, the actual folder on disk would use the corrected title while `build_raw_path()` returns a path based on `title_auto`.

## Affected Code

- `arm/ripper/makemkv.py:962` — `setup_rawpath()` uses `job.title` instead of `job.title_auto`
- `arm/models/job.py:355-359` — `build_raw_path()` correctly uses `title_auto`

## Suggested Fix

In `arm/ripper/makemkv.py:962`, change:
```python
raw_path = os.path.join(str(job.config.RAW_PATH), f"{job.title}_{job.stage}")
```
to:
```python
raw_path = os.path.join(str(job.config.RAW_PATH), f"{job.title_auto or job.title}_{job.stage}")
```
