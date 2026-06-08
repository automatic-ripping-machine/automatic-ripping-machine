# #1706 — Re-queue job if rip succeeded but transcode didn't finish

**Upstream:** https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1706
**Priority:** Low
**Verdict:** FEATURE REQUEST — fully implemented in our fork via separate transcoder service

## Problem

When the rip succeeds but transcoding is interrupted (system restart, driver crash, container restart), there's no way to re-queue just the transcode step. Users must re-rip the entire disc.

## Upstream Reports

- **Reporter:** NVIDIA driver issues on Ubuntu 24.04 prevented transcoding from completing
- Keeps raw files as manual backup but no automated re-queue mechanism
- Flagged as duplicate of #1263 (queueing system)

## Root Cause (Upstream)

In upstream ARM, rip and transcode happen in the same process. If the process is killed mid-transcode, the job is marked as failed with no way to resume just the transcode step.

## Our Fork's Status

**Fully implemented.** Our architecture separates rip and transcode into independent services:

1. **ARM (rip-only):** `arm/ripper/arm_ripper.py` — rips with MakeMKV, persists `raw_path`, sends webhook. No transcoding.

2. **Transcoder service:** `components/transcoder/src/main.py`:
   - `POST /jobs/{job_id}/retry` endpoint re-queues failed transcode jobs
   - `POST /jobs/{job_id}/retranscode` endpoint triggers re-transcoding
   - Job model has `retry_count` column, configurable `max_retry_count` (default 3, max 10)
   - Worker auto-requeues on failure

3. **UI integration:** Retry and re-transcode buttons exposed through the dashboard

Raw files are always preserved because ARM's rip completes independently of transcoding.

## Affected Code

No changes needed — already implemented.

## Suggested Fix

N/A — already addressed by our decoupled architecture.
