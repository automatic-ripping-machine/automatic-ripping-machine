# #1697 — Smarter main feature selection

**Upstream:** https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1697
**Priority:** Low
**Verdict:** FEATURE REQUEST — legitimate use case, requires capturing TINFO chapter count + file size from MakeMKV
**Related:** #1633 (null crash on main feature)

## Problem

The current main feature selection simply picks the longest track. Disney Blu-rays and similar discs include intentionally long decoy tracks (sometimes longer than the actual movie) to confuse ripping software.

## Upstream Reports

- User requests sorting by: (1) highest chapter count, (2) largest file size, (3) lowest track number
- No logs or specific disc examples provided
- No comments from other users or maintainers

## Root Cause

`arm/ripper/makemkv.py:679`:
```python
track = Track.query.filter_by(job_id=job.job_id).order_by(Track.length.desc()).first()
```

This only considers track duration. But MakeMKV provides additional data via TINFO that ARM never captures:
- **TINFO ID 8:** Number of chapters (real movies typically have 15-40+ chapters; decoys have 1-2)
- **TINFO ID 10:** File size in GB
- **TINFO ID 11:** File size in bytes

The `TrackInfoProcessor` class (lines 1025-1113) only captures two TINFO attributes:
- `TrackID.DURATION = 9` (track length)
- `TrackID.FILENAME = 27` (filename)

The `Track` model has no `chapters` or `file_size` columns.

## Affected Code

- `arm/ripper/makemkv.py:677-680` — main feature selection query
- `arm/ripper/makemkv.py:1025-1113` — `TrackInfoProcessor` (limited TINFO parsing)
- `arm/ripper/makemkv.py:181` — `TrackID` enum (missing CHAPTERS, SIZE entries)
- `arm/models/track.py` — `Track` model (no chapters/file_size columns)

## Suggested Fix

1. **Extend `TrackID` enum:**
   ```python
   class TrackID(enum.IntEnum):
       CHAPTERS = 8
       DURATION = 9
       SIZE_GB = 10
       SIZE_BYTES = 11
       FILENAME = 27
   ```

2. **Add columns to `Track` model** + Alembic migration:
   - `chapters` (Integer, nullable)
   - `source_size` (BigInteger, nullable — bytes)

3. **Update `TrackInfoProcessor._handle_tinfo()`** to capture chapters and size

4. **Improve main feature selection** with multi-criteria sort:
   ```python
   track = Track.query.filter_by(job_id=job.job_id) \
       .order_by(Track.chapters.desc().nullslast(),
                 Track.source_size.desc().nullslast(),
                 Track.length.desc()) \
       .first()
   ```

5. Fall back to longest-track if all tracks have the same chapter count (e.g., older DVDs with no chapter info)
