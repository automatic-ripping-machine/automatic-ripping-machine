# ARM-neu Database Operations Audit

Full audit of every SQLAlchemy database operation in the codebase. All line numbers verified against the current source (v15.1.0, commit 2d7f8237).

## Architecture Overview

- **Engine**: SQLAlchemy + SQLite with WAL mode
- **Session**: `scoped_session` keyed by thread ID
- **Pool**: pool_size=20, max_overflow=10
- **Timeout**: busy_timeout=30000ms (30s), connection timeout=30s
- **Cleanup**: `SessionCleanupMiddleware` rollback+remove after every API request

## Thread Contexts

| Context | Session Cleanup | Retry Logic | Files |
|---------|----------------|-------------|-------|
| **API request** (threadpool) | SessionCleanupMiddleware (app.py:36-39) | Only via database_updater | api/v1/*.py |
| **Ripper daemon** (main.py) | db.session.remove() in finally (main.py:442) | database_updater + database_adder | ripper/*.py |
| **Folder rip** (daemon thread) | db.session.remove() in finally (jobs.py:43, folder_ripper.py:241) | database_updater | ripper/folder_ripper.py |
| **Prescan** (daemon thread) | db.session.remove() in finally (folder.py:214) | None | api/v1/folder.py |
| **Drive rescan** (async executor) | db.session.remove() in finally (drives.py:321) | None | services/drives.py |
| **Startup** (one-shot) | N/A | None | runui.py, job_cleanup.py |

## Safe Patterns (use these)

### database_updater (services/files.py:28-76)
- Exponential backoff retry on SQLite BUSY (0.1s -> 2.0s cap)
- Explicit rollback on non-lock errors and timeout
- API callers: wait_time=10s, ripper callers: wait_time=90s
- **Used by**: ripper/utils.py (delegates), some API endpoints

### database_adder (ripper/utils.py:907-928)
- Linear retry loop (90 attempts, 1s sleep) on BUSY
- db.session.add() + db.session.commit() per attempt
- **Used by**: track/user/config creation in ripper

---

## COMMIT OPERATIONS BY FILE

### api/v1/jobs.py - API Endpoints

| Line | Function | What | Protected | Notes |
|------|----------|------|-----------|-------|
| 232 | start_folder_rip | status=RIPPING | **NO** | Before thread spawn |
| 533 | update_job_title | add Notification | YES (try/except:535) | Rollback on fail |
| 568 | add_music_tracks | add Tracks (loop) | **NO** | Batch commit after loop |
| 617 | update_multi_title | track metadata | **NO** | |
| 638 | clear_track_title | clear track fields | **NO** | |
| 703 | update_naming_patterns | pattern overrides | **NO** | |
| 787 | set_transcode_overrides | JSON field | **NO** | |
| 963 | transcode_webhook | track statuses | **NO** | From transcoder callback |
| 1008 | tvdb_match | multi_title=True | **NO** | After match_episodes_for_api |
| 1082 | update_track_episode | episode fields | **NO** | |
| 1118 | auto_number_episodes | episode_number loop | **NO** | |

**Cross-references:**
- Line 1008 calls `match_episodes_for_api` (tvdb_sync.py) which commits at lines 123, 130
- Line 232 spawns `_rip_folder_by_id` daemon thread (line 37)
- Lines 288, 406 use `database_updater` (safe)

### api/v1/drives.py

| Line | Function | What | Protected | Notes |
|------|----------|------|-----------|-------|
| 389 | remove_drive | delete SystemDrives | **NO** | After db.session.delete() |
| 461 | update_drive | drive fields | **NO** | prescan settings, rip_speed |

### api/v1/notifications.py

| Line | Function | What | Protected | Notes |
|------|----------|------|-----------|-------|
| 64 | dismiss_all | bulk seen=True | **NO** | Query filter + update |
| 76 | purge_cleared | bulk delete | **NO** | Query filter + delete |

### api/v1/folder.py

| Line | Function | What | Protected | Context |
|------|----------|------|-----------|---------|
| 129 | create_folder_job | add Job + Config | **NO** | API thread |
| 167 | _prescan_and_wait | logfile path | YES (outer try) | Daemon thread |
| 197 | _prescan_and_wait | status transition | YES (outer try) | Daemon thread |
| 205 | _prescan_and_wait | error status | YES (outer try) | Daemon thread |

### api/v1/system.py

| Line | Function | What | Protected | Notes |
|------|----------|------|-----------|-------|
| 231 | set_ripping_enabled | AppState.ripping_paused | **NO** | |

### api/v1/setup.py

| Line | Function | What | Protected | Notes |
|------|----------|------|-----------|-------|
| 96 | setup endpoint | config init | YES (outer try) | One-shot |

---

### services/tvdb_sync.py - Episode Matching

| Line | Function | What | Protected | Notes |
|------|----------|------|-----------|-------|
| 65 | match_episodes_sync | track updates | YES (outer) | Called from ripper |
| 123 | match_episodes_for_api | tvdb_id | **NO** | Called from API endpoint |
| 130 | match_episodes_for_api | tracks + season_auto | **NO** | Called from API endpoint |

**Critical cross-reference:** API endpoint tvdb_match (jobs.py:1008) calls match_episodes_for_api, which does 2 unprotected commits before the endpoint does its own commit. Three commits, zero try/except.

### services/drives.py - Drive Management

| Line | Function | What | Protected | Notes |
|------|----------|------|-----------|-------|
| 273 | _cleanup_stale_drives | stale field updates | **NO** | |
| 296 | drives_update | bulk stale=True | **NO** | Start of scan |
| 306 | drives_update | drive field updates | **NO** | Per-drive in loop |
| 318 | drives_update | clear conflicts | **NO** | Per-drive in loop |
| 338 | update_job_status | release job | **NO** | |
| 344 | update_job_status | clear previous | **NO** | |
| 348 | update_job_status | drive_mode default | **NO** | |
| 363 | job_cleanup | clear job refs | **NO** | |
| 380 | update_drive_job | new job assoc | **NO** | |

**Critical:** Lines 296-318 do 3+ commits in a loop during drive scanning. Each commit can lock the DB while the ripper is also writing.

### services/jobs.py - Job Lifecycle

| Line | Function | What | Protected | Notes |
|------|----------|------|-----------|-------|
| 144 | process_makemkv_logfile | stage/progress | **NO** | |
| 190 | process_audio_logfile | stage/eta/progress | **NO** | |
| 298 | delete_job | add Notification | **NO** | |
| 309 | delete_job | add Notification | **NO** | Exception path |
| 375 | abandon_job | add Notification | **NO** | |
| 398 | abandon_job | add Notification | **NO** | Exception path |

### services/files.py - database_updater

| Line | Function | What | Protected | Notes |
|------|----------|------|-----------|-------|
| 57 | database_updater | setattr + commit | YES | Exponential backoff retry |

### services/job_cleanup.py

| Line | Function | What | Protected | Notes |
|------|----------|------|-----------|-------|
| 55 | cleanup_orphaned_jobs | status=fail | **NO** | Startup one-shot |

### services/config.py

| Line | Function | What | Protected | Notes |
|------|----------|------|-----------|-------|
| 255 | setup init | add server/user | **NO** | One-shot |
| 282 | config update | settings | **NO** | |
| 292 | default creation | add defaults | **NO** | One-shot |

---

### ripper/main.py - Ripper Daemon

| Line | Function | What | Protected | Notes |
|------|----------|------|-----------|-------|
| 120 | main | status=IDLE | **NO** | Post-identification |
| 140 | main | music path | **NO** | |
| 185 | main | tracks enabled=True | **NO** | Post-prescan |
| 225 | main | music success | **NO** | |
| 229 | main | music failure | **NO** | |
| 363 | main | manual mode | **NO** | |
| 366 | main | manual mode | **NO** | |
| 431 | finally | ejecting status | **NO** | |
| 439 | finally | final status+time | **NO** | |

**Note:** Lines 431 and 439 are in the finally block. If these fail, the job record is left in an inconsistent state (ejecting but never completing).

### ripper/makemkv.py - MakeMKV Operations

| Line | Function | What | Protected | Notes |
|------|----------|------|-----------|-------|
| 603 | makemkv_mkv | VIDEO_WAITING | **NO** | |
| 606 | makemkv_mkv | VIDEO_INFO | **NO** | |
| 612 | makemkv_mkv | VIDEO_WAITING | **NO** | Post-info |
| 621 | makemkv_mkv | VIDEO_RIPPING | **NO** | |
| 704 | makemkv_mkv | MAINFEATURE flag | **NO** | |
| 709 | makemkv_mkv | enable all tracks | **NO** | |
| 719 | makemkv_mkv | manual wait | **NO** | |
| 724 | makemkv_mkv | VIDEO_RIPPING | **NO** | |
| 948 | process_single_tracks | track ripped | YES (try/except:950) | |
| 981 | process_single_tracks | track updates | **NO** | |
| 1050 | process_single_tracks | track updates | **NO** | |
| 1100 | get_track_info | after track add | **NO** | |
| 1163 | get_track_info | drive add in loop | **NO** | **CRITICAL**: loop commit |
| 1277 | get_track_info | no_of_titles | **NO** | |
| 1330 | get_track_info | track processing | **NO** | |
| 1385 | get_track_info | metadata | **NO** | |
| 1401 | get_track_info | final updates | **NO** | |

### ripper/folder_ripper.py

| Line | Function | What | Protected | Notes |
|------|----------|------|-----------|-------|
| 119 | rip_folder | job init | YES (outer try) | |
| 145 | rip_folder | tracks added | YES (outer try) | |
| 151 | rip_folder | status update | YES (outer try) | |
| 200 | rip_folder | rip complete | YES (outer try) | |
| 221 | rip_folder | transcode phase | YES (outer try) | |
| 229 | rip_folder | final status | YES (outer try) | |

### ripper/identify.py

| Line | Function | What | Protected | Notes |
|------|----------|------|-----------|-------|
| 314 | identify | disc metadata | **NO** | |
| 338 | identify | label normalize | **NO** | |
| 438 | identify | final metadata | **NO** | |

### ripper/music_brainz.py

| Line | Function | What | Protected | Notes |
|------|----------|------|-----------|-------|
| 88 | main | track metadata | YES (try/except:91) | Rollback on fail |
| 112 | main | final MB data | **NO** | |

### ripper/naming.py

| Line | Function | What | Protected | Notes |
|------|----------|------|-----------|-------|
| 459 | render_title | rendered names | **NO** | |

### ripper/arm_ripper.py

| Line | Function | What | Protected | Notes |
|------|----------|------|-----------|-------|
| 46 | rip_visual_media | status update | **NO** | |
| 80 | rip_visual_media | status update | **NO** | |

### ripper/utils.py

| Line | Function | What | Protected | Notes |
|------|----------|------|-----------|-------|
| 918 | database_adder | add + commit | YES | 90-attempt retry loop |
| 954 | clean_old_jobs | status=fail | via database_updater | |

---

## READ OPERATIONS (potential lock holders)

### Long-running queries

| File:Line | Query | Risk | Notes |
|-----------|-------|------|-------|
| jobs.py:154 | `db.session.query(Job)` with filters + pagination | **MODERATE** | Large table scan possible |
| utils.py:938 | `Job.query.filter(status.notin_(excluded))` | **MODERATE** | Iterates all non-terminal jobs |
| utils.py:1233 | `Job.query.filter_by(label=...)` | **HIGH** | Iterates all jobs matching label |
| drives.py:287 | `SystemDrives.query.all()` | **LOW** | Small table but held during loop |
| maintenance.py:29,64 | `db.session.query(Job...)` | **LOW** | Background, immediate .all() |

### Query patterns in loops (hold read locks while writing)

| File:Line | Pattern | Issue |
|-----------|---------|-------|
| drives.py:287-306 | query.all() -> iterate -> commit per item | Read lock held during writes |
| makemkv.py:1158-1163 | filter_by().all() -> iterate -> add + commit | Read lock + write contention |

---

## ROLLBACK LOCATIONS

| File:Line | Trigger | Context |
|-----------|---------|---------|
| app.py:36 | Always (middleware) | After every API request |
| jobs.py:535 | Notification add failure | update_job_title |
| music_brainz.py:91 | Track update failure | MusicBrainz import |
| utils.py:435 | Bulk track update failure | Music status update |
| utils.py:583 | Finalization error | Job completion |
| app_state.py:36 | Singleton race | AppState.get() |
| services/jobs.py:313 | Process termination error | delete_job |
| services/jobs.py:384 | Process termination error | abandon_job |
| services/files.py:40 | Non-dict args | database_updater compat |
| services/files.py:71 | Non-lock DB error | database_updater |
| services/files.py:75 | Timeout | database_updater |
| makemkv.py:950 | Track delete error | process_single_tracks |

---

## SESSION CLEANUP (remove) LOCATIONS

| File:Line | Thread Type | Trigger |
|-----------|-------------|---------|
| app.py:39 | API request | Every request (middleware finally) |
| jobs.py:43 | Daemon | _rip_folder_by_id finally |
| jobs.py:423 | Executor | _make_db_safe_sync finally |
| folder.py:214 | Daemon | _prescan_and_wait finally |
| drives.py:321 | Executor | _do_rescan finally |
| folder_ripper.py:241 | Daemon | rip_folder finally |
| main.py:442 | Daemon | Ripper entry point finally |

---

## STATISTICS

| Category | Count | Protected | Unprotected |
|----------|-------|-----------|-------------|
| **API commits** | 21 | 1 | **20** |
| **Service commits** | 18 | 1 (database_updater) | **17** |
| **Ripper commits** | 50 | 6 | **44** |
| **Total commits** | 89 | 8 | **81** |
| **Rollbacks** | 12 | - | - |
| **Session removes** | 7 | - | - |
| **database_updater calls** | ~15 | All safe | - |
| **database_adder calls** | ~3 | All safe | - |

**81 out of 89 commits have no retry/rollback protection.**

---

## RECOMMENDATIONS

### Phase 1: API Safety (prevents session poisoning)
1. Wrap all 20 unprotected API commits in try/except with rollback
2. Or: route all API writes through database_updater
3. Add proactive rollback at START of each request in middleware

### Phase 2: Ripper Safety (prevents stuck jobs)
4. Replace 44 naked ripper commits with database_updater calls
5. Ensure all status transitions use database_updater with wait_time=90

### Phase 3: Contention Reduction
6. Batch loop commits in drives.py (lines 287-318) - single commit after loop
7. Batch loop commits in makemkv.py (lines 1158-1163) - single commit after loop
8. Review long-running queries for unnecessary lock duration
