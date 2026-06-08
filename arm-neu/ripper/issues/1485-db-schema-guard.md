# #1485 — Ripper starts on outdated DB schema

**Upstream:** https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1485
**Priority:** Medium (high impact — can cause silent data corruption)
**Verdict:** REAL BUG — we are fully affected. `check_db_version()` is dead code, ripper has zero schema validation.

## Problem

ARM starts ripping jobs even when the database schema is out of date (Alembic migration head != current DB version). The ripper process launches from udev before the web UI has a chance to run migrations. This can cause crashes, data corruption, or silent data loss when the ripper tries to write to columns that don't exist.

## Upstream Reports

- **Reporter:** polskikrol (upstream collaborator) — upgrading from ARM 2.16.1 to 2.17.5
- Disc was inserted and ripper auto-started via udev before the DB schema was migrated
- UI showed errors when interacting with the rip
- Upstream maintainer (microtechno9000) acknowledged: "Nice catch. Will look at adding in some checks."

## Root Cause

**`check_db_version()` is dead code.** Defined at `arm/services/config.py:44` but **never called anywhere** in our fork. Grep confirms: only the definition exists, plus references in issue files and test comments.

The actual flow:
1. Container starts, UI boots via `runui.py`
2. `runui.py:32` calls `arm_db_check()` — but this only decides whether to run `drives_update()`, it does NOT block ripper operations or auto-migrate
3. Disc inserted, udev fires `docker_arm_wrapper.sh` -> `arm/ripper/main.py`
4. `main.py:38` does `db.init_engine('sqlite:///' + cfg.arm_config['DBFILE'])` — directly connects with **zero schema validation**
5. `setup()` function immediately creates Job objects and writes to the database
6. If the schema changed between versions, the ripper may crash, corrupt data, or silently drop columns

The UI has `arm_db_migrate()` in `config.py:198` but it's only triggered by the user through the web interface. There is no automatic migration and no hard gate.

## Affected Code

- `arm/services/config.py:44` — `check_db_version()` (dead code, never called)
- `arm/ripper/main.py:38` — DB init with no schema check
- `arm/runui.py:32` — `arm_db_check()` (advisory only, doesn't block ripper)
- `arm/database/__init__.py` — DB initialization and migration

## Suggested Fix

Add a schema version check in `main.py` after DB init — compare Alembic head to current DB revision:
```python
from arm.services.config import arm_db_check
db_status = arm_db_check()
if not db_status["db_current"]:
    logging.critical("Database schema is out of date (head: %s, db: %s). "
                     "Please run migrations before ripping.",
                     db_status["head_revision"],
                     db_status.get("db_revision"))
    sys.exit(1)
```

Alternatively, run migration in `arm_user_files_setup.sh` before udev is started, guaranteeing the schema is current before any ripper process can fire. This is the most robust approach — the ripper should never have to decide about migrations.

Also consider removing the dead `check_db_version()` function to reduce confusion.
