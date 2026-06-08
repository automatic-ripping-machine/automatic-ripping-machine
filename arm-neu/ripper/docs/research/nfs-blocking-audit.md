# NFS Blocking Audit - ARM API Responsiveness

## Problem
During large NFS file operations (scratch→shared copy), the ARM API becomes
unresponsive for 5-10 minutes. The UI shows ARM as unreachable.

## Root Cause
NFS `statvfs()` syscalls enter kernel D-state (uninterruptible sleep) when
the NFS client is saturated by large file copies. D-state cannot be interrupted
by signals, cancelled, or killed. This affects ANY process that touches the
NFS mount, not just the process doing the copy.

## Key Finding
Converting `async def` → `def` (threadpool) does NOT fix this. Both use
bounded thread pools. A D-state thread never returns, so all pool threads
exhaust under continuous requests. The fix must avoid `statvfs()` entirely
during NFS stalls.

## Affected Codepaths

### 1. ARM Stats Endpoint (system.py:78) - HIGHEST IMPACT
- `psutil.disk_usage(path)` on NFS media paths
- Polled by UI every few seconds
- Fix: Cache with TTL, refresh via background subprocess

### 2. File Browser Service (files.py:73)
- `os.statvfs(path)` for directory size
- Fix: Same disk usage cache

### 3. Rip Thread NFS Copy (utils.py:163)
- `shutil.copy2()` per file, scratch→NFS shared
- Causes the NFS saturation that triggers D-state for others
- Fix: rsync subprocess with progress + timeout

### 4. Transcoder Source/Output Copy (transcoder.py:636-744)
- `shutil.copytree/copy2/move` in async function
- Blocks transcoder event loop (health goes unreachable)
- Fix: asyncio.create_subprocess_exec rsync (separate repo)

### 5. File Browser Move/Delete (file_browser.py:317,338)
- `shutil.move`, `shutil.rmtree`
- In threadpool (PR #150), acceptable for user-initiated ops

### 6. Maintenance (maintenance.py:185,240)
- `shutil.rmtree` on media paths
- Infrequent, acceptable

## Fix Strategy

### Stats/File Browser: Cached Disk Usage
- Background thread refreshes disk usage every 30s via subprocess
- Subprocess has a 3s timeout - if NFS stalls, serves stale cache
- API endpoint reads from cache (never calls statvfs directly)
- Subprocess can be abandoned (unlike threads, D-state subprocesses
  don't block the parent)

### Rip Copy: rsync Subprocess
- Replace `shutil.copy2` loop with `rsync` subprocess
- Parse rsync progress output for per-file status updates
- Subprocess can be killed if stalled (timeout)
- ARM API stays responsive because it's not doing the I/O

### Transcoder: asyncio Subprocess (separate repo)
- Replace `shutil.copytree/move` with `asyncio.create_subprocess_exec`
  running rsync
- Event loop stays responsive
- Health endpoint stays alive during copies
