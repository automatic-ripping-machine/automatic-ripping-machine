# #1558 — Docker container does not release CDROM drive

**Upstream:** https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1558
**Priority:** Medium
**Verdict:** REAL BUG — we are affected (same eject code, no umount before eject)

## Problem

After MakeMKV completes, the drive may still be mounted. The `eject` command fails with "device busy". In Docker with `privileged: true`, this is common because the host kernel's auto-mounter may have mounted the disc filesystem. Multiple users across different hardware confirm the issue.

## Upstream Reports

- **Multiple users:** HP EliteDesk 800 G1, G3, various external USB drives, VMs
- Key log pattern:
  ```
  INFO ARM: MakeMKV exits gracefully.
  ERROR ARM: eject: cannot open /dev/sr0: Device or resource busy
  INFO ARM: Releasing current job from drive
  ```
- `grep /dev/sr0 /proc/self/mounts` confirms device is still mounted post-rip
- **User-discovered workaround:** Adding `--force` to the `eject` command

## Root Cause

The eject flow has a gap — no `umount` between MakeMKV finishing and the eject attempt:

1. `identify.py` mounts the disc for identification, then unmounts at line 238
2. `utils.py:661` (`save_disc_poster()`) remounts the disc, extracts poster, unmounts — but uses `os.system()` with no error handling
3. MakeMKV may internally mount the disc or hold file descriptors
4. `makemkv()` finishes and calls `job.eject()` at line 857
5. `SystemDrives.eject()` at `arm/models/system_drives.py:231` runs `eject --verbose --cdrom --scsi /dev/sr0` — **no umount first**
6. If the disc is still mounted from a prior step, eject fails with "device busy"

The `eject` manpage says it auto-unmounts, but this may fail in Docker containers where mount namespaces differ.

**Additional issue:** `save_disc_poster()` at `arm/ripper/utils.py:661` uses `os.system(f"mount {job.devpath}")` which is both a shell injection risk and provides no error handling.

## Affected Code

- `arm/models/system_drives.py:209-237` — `SystemDrives.eject()` (no umount, no --force)
- `arm/ripper/utils.py:661-668` — `save_disc_poster()` (os.system mount/umount)
- `arm/ripper/makemkv.py:857` — `job.eject()` call site

## Suggested Fix

**Primary:** Add explicit `umount` before eject in `SystemDrives.eject()`:
```python
def eject(self, method="eject"):
    # Unmount before ejecting to avoid "device busy" errors
    try:
        arm_subprocess(["umount", self.mount], check=False)
    except Exception:
        pass  # Best effort
    cmd = ["eject", "--force", "--verbose"] + options + methods[method] + [self.mount]
    ...
```

**Secondary:** Fix `save_disc_poster()` to use `subprocess.run(["umount", job.devpath])` instead of `os.system()`
