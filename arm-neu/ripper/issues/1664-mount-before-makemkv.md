# #1664 — `save_disc_poster()` leaves disc mounted before MakeMKV

- **Upstream:** [#1664](https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1664)
- **Verdict:** REAL BUG
- **Status:** FIXED

## Problem

`save_disc_poster()` in `arm/ripper/utils.py` uses `os.system("mount ...")` / `os.system("umount ...")` with zero error handling. If unmount fails (or the function exits early), the disc stays mounted when MakeMKV tries to get exclusive access → "no usable optical drives".

The function is called in `arm_ripper.py` **after** identify and **before** `makemkv()`.

## Root Cause

- `os.system()` ignores return codes — mount/umount failures are silent
- No `try/finally` — if ffmpeg or `os.path.isfile()` raises, umount is skipped
- Shell injection risk: `job.devpath` is interpolated directly into shell command

## Fix

Rewrote `save_disc_poster()` to:
1. Use `subprocess.run()` instead of `os.system()` (proper error handling, no shell injection)
2. Wrap in `try/finally` so umount always runs
3. Log errors from mount/umount failures
4. Early return for non-DVD or RIP_POSTER disabled

## Tests

- `TestSaveDiscPoster.test_happy_path_ntsc_poster` — verifies mount→ffmpeg→umount sequence
- `TestSaveDiscPoster.test_umount_always_called_even_if_ffmpeg_fails` — verifies umount runs on exception
- `TestSaveDiscPoster.test_non_dvd_is_noop` — bluray skips entirely
- `TestSaveDiscPoster.test_rip_poster_disabled_is_noop` — disabled config skips entirely
