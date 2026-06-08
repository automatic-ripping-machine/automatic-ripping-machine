# Upstream Issue Tracker

Relevant open issues from [upstream ARM](https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues) that affect our fork. Each file contains root cause analysis, affected code paths, and suggested fixes.

## High Priority

| File | Upstream | Verdict | Summary |
|------|----------|---------|---------|
| [1711-drive-readiness-timeout.md](1711-drive-readiness-timeout.md) | [#1711](https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1711) | REAL BUG | 10s drive readiness timeout too short; multiple udev triggers |
| [1667-cds-error-prevents-rip.md](1667-cds-error-prevents-rip.md) | [#1667](https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1667) | ENV + BUG | USB re-enumeration breaks device node mapping; CDS_ERROR persists |
| [1539-stuck-at-info-status.md](1539-stuck-at-info-status.md) | [#1539](https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1539) | REAL BUG | No timeout on makemkvcon subprocess; job stuck at "info" forever |
| [1545-makemkv-does-not-start.md](1545-makemkv-does-not-start.md) | [#1545](https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1545) | ENV + minor bug | MakeMKV 1.18.x regression hangs disc:9999 scan; `:d` format on None |
| [1633-mainfeature-null-crash.md](1633-mainfeature-null-crash.md) | [#1633](https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1633) | BUG + FR | Main feature selection crashes if no tracks; no fallback to rip-all |
| [1161-late-title-erases-rips.md](1161-late-title-erases-rips.md) | [#1161](https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1161) | LARGELY FIXED | Late title change erases rips; our fork removed move_files pipeline |
| [1636-title-search-stuck.md](1636-title-search-stuck.md) | [#1636](https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1636) | REAL BUG | DVDs stuck in "waiting" after Title Search; `sleep_check_process` infinite wait |
| [1298-data-rip-false-success.md](1298-data-rip-false-success.md) | [#1298](https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1298) | REAL BUG | Data rip fails but job shows SUCCESS; main.py overwrites FAILURE status |
| [1664-mount-before-makemkv.md](1664-mount-before-makemkv.md) | [#1664](https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1664) | ALREADY FIXED | `save_disc_poster()` leaves disc mounted; MakeMKV can't get exclusive access |
| [1651-data-disc-label-collision.md](1651-data-disc-label-collision.md) | [#1651](https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1651) | ALREADY FIXED | Data disc with same label silently discarded; raw rip destroyed |
| [1639-settings-not-persisting.md](1639-settings-not-persisting.md) | [#1639](https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1639) | ALREADY FIXED | `importlib.reload()` creates orphaned dict; settings don't persist |

## Medium Priority

| File | Upstream | Verdict | Summary |
|------|----------|---------|---------|
| [1558-cdrom-not-released.md](1558-cdrom-not-released.md) | [#1558](https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1558) | REAL BUG | No umount before eject; "device busy" in Docker |
| [1622-permission-detection-fails.md](1622-permission-detection-fails.md) | [#1622](https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1622) | BUG (low) | Script checks ownership before fixing it; mitigated by our compose |
| [1485-db-schema-guard.md](1485-db-schema-guard.md) | [#1485](https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1485) | REAL BUG | `check_db_version()` is dead code; ripper has zero schema validation |
| [1559-trixie-udev-breaks-drives.md](1559-trixie-udev-breaks-drives.md) | [#1559](https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1559) | ENV (mitigated) | Debian Trixie udev changes; our `/dev/sr*` fallback handles it |
| [1707-tracks-not-populated-manual.md](1707-tracks-not-populated-manual.md) | [#1707](https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1707) | ALREADY FIXED | Track list empty in manual mode; our fork populates before wait |
| [1294-tv-series-label-lost.md](1294-tv-series-label-lost.md) | [#1294](https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1294) | BUG / design | TV series loses S/D label info; partially mitigated by arm_matcher |
| [1297-wrong-main-title.md](1297-wrong-main-title.md) | [#1297](https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1297) | BUG / design | Wrong main title track; skip_transcode_movie removed; see #1697 |
| [1475-success-but-no-file.md](1475-success-but-no-file.md) | [#1475](https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1475) | ALREADY FIXED | Success but no file; fixed via `_reconcile_filenames()` + no move_files |

## Low Priority

| File | Upstream | Verdict | Summary |
|------|----------|---------|---------|
| [1697-smarter-mainfeature-selection.md](1697-smarter-mainfeature-selection.md) | [#1697](https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1697) | FEATURE REQ | Need to capture TINFO chapter count + size for better track selection |
| [1666-pushover-support.md](1666-pushover-support.md) | [#1666](https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1666) | CONFIG ISSUE | Pushover already works via arm.yaml; apprise.yaml path is dead end |
| [1613-mqtt-apprise-support.md](1613-mqtt-apprise-support.md) | [#1613](https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1613) | FEATURE REQ | Needs `paho-mqtt` dependency and config surface for MQTT |
| [1186-nfs-chown-failure.md](1186-nfs-chown-failure.md) | [#1186](https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1186) | BUG + ENV | chown fails on NFS mounts; mitigated by docker-compose; see #1622 |
| [1336-dashes-in-title-lookup.md](1336-dashes-in-title-lookup.md) | [#1336](https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1336) | LARGELY FIXED | arm_matcher handles hyphens via compound word fallback; sequel margins narrower |
| [1706-requeue-failed-transcode.md](1706-requeue-failed-transcode.md) | [#1706](https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1706) | ALREADY FIXED | Re-queue interrupted transcode; fully implemented via our transcoder |

## Verdict Key

| Label | Meaning |
|-------|---------|
| REAL BUG | Code defect in ARM that we share |
| ENV | Environmental issue (hardware, OS, third-party software) |
| ENV + BUG | Environmental trigger with a real code defect making it worse |
| BUG (low) | Real bug but mitigated in our setup |
| FEATURE REQ | Missing functionality, not a defect |
| CONFIG ISSUE | Works through a different config path; documentation/UX problem |
| LARGELY FIXED | Bug exists upstream but our architecture eliminates most of it |
| ALREADY FIXED | Issue exists upstream but already resolved in our fork |

## Stats

- **25 issues tracked** (12 original + 13 new)
- **8 already/largely fixed** in our fork (#1161, #1475, #1707, #1706, #1336, #1664, #1651, #1639)
- **6 real bugs** we still share (#1711, #1539, #1633, #1636, #1298, #1558)
- **2 environmental + bug** (#1667, #1545)
- **4 mitigated/low** (#1622, #1485, #1559, #1186)
- **3 feature/config** (#1697, #1666, #1613)
- **2 design limitations** (#1294, #1297)
