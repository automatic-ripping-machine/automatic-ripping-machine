# udev and Long-Running Processes: Research Summary

## 1. Default event_timeout and Kill Behavior

- **Default timeout**: **180 seconds** (`event_timeout=` in `/etc/udev/udev.conf`, or `--event-timeout=` CLI flag).
- **Default signal**: **SIGKILL** (`timeout_signal=` in udev.conf, or `--timeout-signal=` CLI flag). Configurable since systemd v246. Can be changed to SIGABRT for debugging worker timeouts.
- **What gets killed**: Both the udevd **worker process** and all **spawned processes** receive the signal. The manpage explicitly states: "both workers and spawned processes will be killed using this signal."

## 2. `exec` in a RUN+= Script and Timeout Inheritance

When a RUN+= script uses `exec`, the exec'd process **replaces** the shell process in the same PID. Since udevd tracks the worker's child PID (the one it forked for RUN+=), the exec'd process inherits that PID and is subject to the same timeout. There is no escape via `exec`.

More importantly, udevd runs inside a **systemd cgroup** (`systemd-udevd.service`). All child processes, regardless of `exec`, `fork`, `setsid`, or double-fork, remain in the same cgroup. When the timeout fires, systemd kills everything in that cgroup scope.

## 3. Recommended Approaches for Long-Running Processes from udev

The udev(7) manpage is explicit:

> "Starting daemons or other long-running processes is not allowed; the forked processes, **detached or not**, will be **unconditionally killed** after the event handling has finished."

### Recommended approaches (best to worst):

| Method | How | Pros | Cons |
|--------|-----|------|------|
| **`SYSTEMD_WANTS=`** | `ENV{SYSTEMD_WANTS}="my-handler@%k.service"` in udev rule | Fully supported, proper lifecycle, logs in journald, dependencies work | Requires a .service unit file |
| **`systemd-run --no-block`** | `RUN+="/usr/bin/systemd-run --no-block /path/to/script"` | No .service file needed, escapes cgroup immediately | Transient unit, less control over dependencies |
| **`systemctl start`** | `RUN+="/usr/bin/systemctl start my.service"` | Works, explicit | Blocks until service starts (use `--no-block` to avoid) |
| **`at now`** | `RUN+="/usr/bin/at -f /path/to/script now"` | Simple, escapes udev entirely | Requires atd, no systemd integration |

### Methods that DO NOT WORK:

- **`&` (backgrounding)** -- still in same cgroup, killed on timeout
- **`setsid`** -- new session but same cgroup, killed on timeout
- **`nohup`** -- only protects against SIGHUP, not SIGKILL
- **`disown`** -- shell-level only, does not escape cgroup
- **`daemonize` / double-fork** -- same cgroup, killed on timeout

## 4. flock Behavior When Process is SIGKILL'd

**flock advisory locks are automatically released when the process is killed**, including by SIGKILL.

From flock(2):
> "The lock is released either by an explicit LOCK_UN operation on any of [the] duplicate file descriptors, or when **all such file descriptors have been closed**."

When a process is SIGKILL'd, the kernel closes all its file descriptors as part of process teardown. This releases any flock locks. This is guaranteed and immediate on local filesystems.

**Caveat**: On NFS, flock locks may NOT be properly released on SIGKILL due to the network-based lock protocol (lockd/NLM). This is documented in the flock(2) manpage notes section.

**Caveat for fork/dup**: If a child process inherited (via `fork()`) or duplicated (via `dup()`) the lock's file descriptor, the lock is NOT released until ALL copies of that fd are closed. Killing only the parent leaves the lock held by the child.

## 5. `start_new_session=True` and SIGKILL Protection

`start_new_session=True` in Python's `subprocess.Popen` calls `setsid()`, which:
- Creates a new **session** (new SID)
- Creates a new **process group** (new PGID)
- Detaches from the controlling terminal

**Does it protect from parent's SIGKILL?** **Yes, partially**:
- When the parent is SIGKILL'd, the child survives because SIGKILL is not propagated to other sessions/process groups.
- The child becomes an orphan and is re-parented to PID 1 (init/systemd).

**Does it protect from udev's timeout kill?** **No**:
- udevd uses **cgroup-based killing**, not process-group-based killing.
- `setsid()` changes the session but does NOT move the process out of its cgroup.
- The child remains in `systemd-udevd.service`'s cgroup and will be killed on timeout.

## 6. Comparison of Detaching Methods

| Method | New Session | New PG | Escapes Cgroup | Survives udev timeout | Survives parent SIGKILL |
|--------|-------------|--------|----------------|----------------------|------------------------|
| `setsid` | Yes | Yes | **No** | **No** | Yes |
| `nohup` | No | No | **No** | **No** | Yes (SIGHUP only) |
| `systemd-run --no-block` | Yes | Yes | **Yes** (new transient unit) | **Yes** | **Yes** |
| `at now` | Yes | Yes | **Yes** (atd's cgroup) | **Yes** | **Yes** |
| `daemonize` / double-fork | Yes | Yes | **No** | **No** | Yes |
| `start_new_session=True` (Python) | Yes | Yes | **No** | **No** | Yes |
| `SYSTEMD_WANTS=` | N/A | N/A | **Yes** (own unit) | **Yes** | **Yes** |

**The only reliable methods are those that create a new systemd scope/service**: `systemd-run`, `systemctl start`, or `SYSTEMD_WANTS=`.

## 7. Caveats: Detaching from udev While Holding an flock

If your udev RUN+= script acquires an flock and then spawns a long-running child:

1. **If the child inherits the fd** (via fork without closing it): The lock is shared between parent and child. When udev kills the parent on timeout, the child still holds the lock via its inherited fd -- but if the child is also killed (same cgroup), the lock is released.

2. **If using `systemd-run` to escape**: The new process is in a different cgroup and survives. But it does NOT inherit file descriptors from the udev script -- `systemd-run` starts a clean process. The flock must be re-acquired in the new process. The original lock is released when the udev worker exits.

3. **Race condition**: If the udev script acquires a lock, launches a service via `systemd-run`, and then exits (releasing the lock), there is a window where the lock is unheld before the service re-acquires it. Another instance could grab it in between.

4. **Recommended pattern**: Use the flock only in the long-running service itself (started via `systemd-run` or `SYSTEMD_WANTS=`), not in the udev script. The udev script should be a thin launcher that does nothing requiring a lock.

## Summary for ARM

For ARM's udev rule that launches the ripping process:
- The current approach of running a long process from RUN+= is fundamentally at odds with udev's design
- `setsid`, `nohup`, backgrounding (`&`), and `start_new_session=True` **will not help** because udev uses cgroup-based killing
- **Best approach**: `RUN+="/usr/bin/systemd-run --no-block /path/to/arm_wrapper.sh %k"` or use `SYSTEMD_WANTS=` with a parameterized service unit
- flock for drive exclusion should be acquired inside the long-running service, not in the udev launcher script

## Sources

- [udev(7) manpage](https://man7.org/linux/man-pages/man7/udev.7.html)
- [systemd-udevd(8) manpage](https://www.man7.org/linux/man-pages/man8/systemd-udevd.8.html)
- [udev.conf(5) manpage](https://man7.org/linux/man-pages/man5/udev.conf.5.html)
- [flock(2) manpage](https://man7.org/linux/man-pages/man2/flock.2.html)
- [bkhome: How to run long-time process on udev event](https://www.bkhome.org/news/202012/how-to-run-long-time-process-on-udev-event.html)
- [systemd for Administrators: cgroup process tracking](http://0pointer.de/blog/projects/systemd-for-admins-2.html)
- [systemd/systemd#30436: worker timeout kills](https://github.com/systemd/systemd/issues/30436)
