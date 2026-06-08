# Research: FastAPI + NFS Stall Threadpool Exhaustion

Date: 2026-03-27

## Question 1: Does converting `async def` to `def` help with NFS-stalled `statvfs()`?

**Partially, but it does NOT prevent exhaustion.**

When a FastAPI handler is `def` (sync), Starlette runs it via `anyio.to_thread.run_sync` in a
bounded threadpool. This keeps the asyncio event loop free, so other `async def` endpoints remain
responsive. However, `statvfs()` on a stalled NFS mount enters **D-state (uninterruptible sleep)**
at the kernel level. The thread is stuck indefinitely -- it cannot be interrupted even by `SIGKILL`.

If enough requests hit the `disk_usage()` path while NFS is stalled, **all 40 threadpool threads
will be consumed**, and every subsequent sync handler (`def`) will queue behind them. The event loop
stays alive, but no sync work can proceed.

**Sources:**
- [psutil#1931](https://github.com/giampaolo/psutil/issues/1931) -- confirmed D-state hang on NFS
- [Starlette threadpool docs](https://starlette.dev/threadpool/) -- 40-token default, shared pool

## Question 2: Default threadpool size -- is 40 enough?

**Default is 40 threads (AnyIO CapacityLimiter tokens).** This is a shared pool used by:
- All `def` endpoint handlers
- `FileResponse` serving
- `UploadFile` handling
- Sync background tasks
- FastAPI sync dependency injection

40 threads is **not enough** to absorb NFS stalls that last minutes. A single stalled NFS mount
with a dashboard polling `/system/stats` every 5 seconds will consume all 40 threads in ~3 minutes.

You can increase it via lifespan:
```python
import anyio
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app):
    limiter = anyio.to_thread.current_default_thread_limiter()
    limiter.total_tokens = 200
    yield
```

But increasing threads is a band-aid -- D-state threads never return, so any finite pool will
eventually exhaust.

## Question 3: `async def` + `asyncio.to_thread()` vs plain `def`

**They are functionally equivalent for this problem.** Both use the same AnyIO threadpool.

- `def` handler: Starlette calls `anyio.to_thread.run_sync(handler)`
- `async def` + `await asyncio.to_thread(blocking_fn)`: Uses `asyncio`'s default executor

The slight difference: `asyncio.to_thread` uses Python's `ThreadPoolExecutor` (default
`min(32, os.cpu_count() + 4)` threads), while Starlette's `run_sync` uses AnyIO's
`CapacityLimiter` (40 tokens). Both are bounded and both will exhaust.

**Neither approach helps** because the underlying `statvfs()` syscall is stuck in kernel D-state.

## Question 4: Recommended pattern for endpoints that may block on NFS

**The only reliable pattern is: never call `statvfs()` on a potentially-stalled mount in the
request path.** Specific strategies:

### Strategy A: Cached background probe (RECOMMENDED)
Run `disk_usage()` in a **separate process** on a timer. Cache the result. Serve cached data
from the API endpoint. If the probe process hangs, kill it after a timeout.

```python
import subprocess, json, time, threading

_disk_cache = {}
_cache_lock = threading.Lock()
CACHE_TTL = 30  # seconds

def _probe_disk(path: str) -> dict | None:
    """Run disk_usage in a subprocess with timeout."""
    try:
        result = subprocess.run(
            ["python3", "-c", f"import psutil, json; u=psutil.disk_usage('{path}'); "
             f"print(json.dumps({{'total':u.total,'used':u.used,'free':u.free,'percent':u.percent}}))"],
            capture_output=True, text=True, timeout=5
        )
        return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, Exception):
        return None

def get_disk_usage_cached(path: str) -> dict | None:
    with _cache_lock:
        entry = _disk_cache.get(path)
        if entry and time.time() - entry["ts"] < CACHE_TTL:
            return entry["data"]
    # Probe in subprocess
    data = _probe_disk(path)
    if data:
        with _cache_lock:
            _disk_cache[path] = {"data": data, "ts": time.time()}
    return data
```

### Strategy B: `subprocess.run` with timeout (simpler)
Use `stat -f` or `df` in a subprocess instead of Python's `os.statvfs()`:

```python
import subprocess
def safe_disk_usage(path: str, timeout: float = 3.0) -> dict | None:
    try:
        r = subprocess.run(
            ["stat", "-f", "-c", "%S %b %f %a", path],
            capture_output=True, text=True, timeout=timeout
        )
        bsize, blocks, bfree, bavail = r.stdout.strip().split()
        total = int(bsize) * int(blocks)
        free = int(bsize) * int(bavail)
        used = total - int(bsize) * int(bfree)
        return {"total": total, "used": used, "free": free,
                "percent": round(used / total * 100, 1) if total else 0}
    except (subprocess.TimeoutExpired, Exception):
        return None
```

**Why subprocess works when threads don't:** A subprocess that enters D-state can be abandoned
(its PID reaped eventually when NFS recovers or mount is force-unmounted). The parent process
is unaffected. A thread in D-state, however, permanently consumes a slot in the threadpool
and cannot be killed.

### Strategy C: Skip when known-stale
Track NFS health. If a path timed out recently, skip it for a cooldown period:

```python
_stale_paths: dict[str, float] = {}
STALE_COOLDOWN = 120  # seconds

def is_path_stale(path: str) -> bool:
    ts = _stale_paths.get(path)
    return ts is not None and time.time() - ts < STALE_COOLDOWN

def mark_stale(path: str):
    _stale_paths[path] = time.time()
```

## Question 5: Making `statvfs()`/`disk_usage()` non-blocking

| Approach | Works? | Notes |
|----------|--------|-------|
| Thread + timeout | NO | Thread enters D-state, never returns. `threading.Timer` can't kill it. |
| `signal.alarm` (SIGALRM) | NO | D-state is immune to signals. |
| `asyncio.to_thread` + `wait_for` | NO | `asyncio.wait_for` cancels the coroutine but the underlying thread stays stuck. |
| **Subprocess + timeout** | **YES** | `subprocess.run(timeout=N)` sends SIGKILL after timeout. The subprocess is D-state but the parent continues. The zombie is reaped when NFS recovers. |
| **Separate process (multiprocessing)** | **YES** | Same principle. `Process.join(timeout)` + `Process.kill()`. |
| **Cache with background refresh** | **YES** | Best approach. Never blocks the request path. |
| NFS mount option `soft,timeo=10` | **PARTIAL** | Makes NFS return EIO after timeout instead of hanging. Requires mount config change. |
| NFS mount option `intr` | **PARTIAL** | Allows SIGINT to interrupt. Deprecated on modern kernels (NFSv4 ignores it). |

## Question 6: Known patterns / issues

- **Datadog agent** solved this exact problem by running `statvfs` in a separate thread with a
  timeout, then abandoning the thread if it hangs. They accept the leaked thread as a trade-off.
  ([Datadog engineering blog: The Trouble with Mounting](https://www.datadoghq.com/blog/engineering/the-trouble-with-mounting/))

- **psutil#1931**: Confirmed that `psutil.disk_usage()` and `psutil.disk_partitions()` both hang
  on stale NFS. The psutil maintainer (giampaolo) noted there is nothing the library can do --
  the kernel syscall is uninterruptible.

- **Ansible#25046**: Ansible fact gathering hangs on stale NFS mounts for the same reason.

- **FastAPI#4495, #6512**: FastAPI gets stuck when all threadpool threads are blocked. The fix is
  always to avoid blocking the threadpool with long-running operations.

## Recommendation for ARM

The `/system/stats` endpoint in `arm/api/v1/system.py` (line 78) calls `psutil.disk_usage(path)`
synchronously for up to 3 NFS-mounted paths. The `get_paths` endpoint (line 185) calls
`os.path.exists()` which also does a `stat()` that can hang.

**Recommended fix:**
1. Use Strategy A (cached subprocess probe) for disk usage.
2. Run a background task every 30s that probes each path in a subprocess with a 5s timeout.
3. The API endpoint returns cached results (with a `stale` flag if cache is old).
4. If a path times out, mark it stale and skip it for 2 minutes.
5. Also protect `get_paths` -- `os.path.exists()` can hang on NFS too.
