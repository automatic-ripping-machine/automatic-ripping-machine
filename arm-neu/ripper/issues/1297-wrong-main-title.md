# #1297 — Wrong Main Title Track selected

**Upstream:** https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1297
**Priority:** Medium
**Verdict:** REAL BUG / design limitation — tracked in #1697; `skip_transcode_movie` removed in our fork
**Related:** #1697 (smarter main feature selection), #1633 (null crash)

## Problem

ARM selects the wrong track as the "main title." The reporter ripped "The Nightmare Before Christmas" and ARM picked `title_t53` (37 min, 1.5 GB, 24576 kbps) over `title_t10` (76 min, 1.4 GB, 37666 kbps) — the actual movie. The shorter track had a larger file size due to higher per-second bitrate.

## Upstream Reports

- **Reporter:** "The Nightmare Before Christmas" — wrong track selected by file size
- Upstream `skip_transcode_movie` logic selected by largest file size, not by duration
- MAINFEATURE mode selects by longest duration — more reliable but still vulnerable to decoy tracks

## Root Cause

Two separate code paths had different selection logic:
1. **MAINFEATURE mode:** selects by `Track.length.desc()` (duration) — more reliable
2. **SKIP_TRANSCODE movie mode:** selected by largest file size — this hit the reporter

## Our Fork's Status

**Partially fixed.** We removed HandBrake/FFmpeg transcoding entirely (commit `66ec6d6`), so `skip_transcode_movie` and the file-size selection path no longer exist.

The MAINFEATURE duration-based selection at `arm/ripper/makemkv.py:679` still exists and is vulnerable to longer-than-movie decoy tracks (Disney Blu-rays).

## Affected Code

- `arm/ripper/makemkv.py:677-679` — MAINFEATURE selection by duration only

## Suggested Fix

Same as #1697 — implement multi-criteria selection using chapter count and file size from MakeMKV TINFO. See `issues/1697-smarter-mainfeature-selection.md` for the full plan.
