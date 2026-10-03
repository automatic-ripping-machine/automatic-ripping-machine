# ARM-v3 Potential Bugs

Leads collected during the 2026-09-02 full sweep with the ARM-v3 devtools MCP
(75 tools) and the jcodemunch structural index. These are NOT confirmed bugs -
each entry says what the signal is, why it is not confirmed, and what would
confirm it. Confirmed findings live in `arm-devtools-v3-bug-notes.md`.

## 1. Hardware-transcode detection silently fails where HandBrakeCLI is not on PATH

- **Signal:** three `ERROR` entries in the UI log:
  `utils.check_hw_transcode_support - Call to handbrake failed with code: 127`
  (exit 127 = command not found). Verified: `command -v HandBrakeCLI` is empty
  in the UI container.
- **Why not confirmed:** this dev container doesn't install HandBrakeCLI;
  production installs do, and the check presumably degrades to "no hardware
  transcode". Unknown whether any config value is written wrongly when it
  fails.
- **What would confirm:** run the check on a production-style install and
  compare the persisted hardware-transcode flags.

## 2. UI git update check fails silently

- **Signal:** `utils.git_check_updates - Unable to check if we are on the
  latest commit` in the UI log.
- **Why not confirmed:** likely environment (no network to github from the
  dev container, or no git identity). If it fails silently on production
  too, users believe they are current when they are not.
- **What would confirm:** check `git_check_updates`' fallback behaviour
  when the remote is unreachable.

## 3. Forty-nine modules flagged "unstable" (coupling)

- **Signal:** `jcm_get_repo_health` radar: coupling score 54.4, with 49 of
  215 files above the instability threshold.
- **Why not confirmed:** a coupling metric, not a defect. High outward
  dependency concentrates change risk but proves nothing by itself.
- **What would confirm:** list the 49 files and review the top offenders for
  actual structural problems (e.g. `ui` importing ripper internals).

## 4. Test-gap signal near zero

- **Signal:** health radar `test_gap` raw 0.1% - almost no evidence in the
  index of functions being exercised by test files.
- **Why not confirmed:** the index infers test coverage from imports, not
  from actual pytest runs, and v3's test suite is known-broken (see the bug
  report), so the metric is pessimistic by construction.
- **What would confirm:** a real coverage run once the test infra is fixed.

## 5. Run-order masking in the test suite

- **Signal:** the model-test app-context failure reproduces standalone but
  not in the full suite - a context-pushing test happens to run first and
  masks it.
- **Why not confirmed:** one demonstrated case, not proof of a class. But
  anything else that depends on test order would be masked the same way.
- **What would confirm:** run each test file standalone (the MCP's
  `run_tests_for_file` makes this cheap) and diff against the full-suite
  result.

## 6. No static type checking on arm/ui

- **Signal:** `run_type_check` reports pyright not installed in the
  container. The 9 route crashes in the bug report are precisely the class
  of error a type checker catches (`Job.query.get(None)` dereferenced).
- **Why not confirmed:** absence of a checker proves nothing about specific
  code; it only means that class of bug is undetectable by tooling today.
- **What would confirm:** `pip install pyright` in the container and run
  `run_type_check` - every new warning is a potential-bug candidate.

## 7. Form/POST routes never probed

- **Signal:** `check_route_health` and this sweep only exercised GETs. The
  form posts (`/save_settings`, `/save_ui_settings`, `/save_abcde_settings`,
  `/jobdetailload`, `/systeminfo`, ...) have never been hit with missing or
  malformed fields.
- **Why not confirmed:** nothing failed - they were not tested at all.
- **What would confirm:** a POST-equivalent health check (or careful manual
  probing) on a dev instance; a bare POST that 500s would be a real find.

## 8. The devtools change is the repo's top complexity hotspot

- **Signal:** `jcm_get_hotspots` top 10 are all devtools files
  (`build_tools` cyclomatic 62, `register_routes` 31, ...), and the health
  radar flags complexity at 91.66.
- **Why not confirmed:** complexity is a maintainability metric, not a bug,
  and `build_tools`' figure is inflated by its single-literal tool list.
- **What would confirm:** nothing to confirm - it is a known property of
  the change, listed so the maintainer sees the whole picture.

## 9. Type-checker finding confirmed: 125 errors across arm/ui

- **Update 2026-09-02:** entry 6 above asked what installing pyright would
  show. It was installed and run live (`pyright 1.1.411`, `run_type_check`):
  **125 errors** across arm/ui.
- The nine crashing routes are confirmed statically - the exact
  optional-member-access sites appear in the output (arm/ui/jobs/routes.py
  51/202/249, arm/ui/logs/routes.py 104, among many).
- New confirmed defect: arm/ui/migrations/env.py:94 uses an undefined
  `logger` (see bug report entry 9).
- Also flagged: arm/ui/jobs/metadata.py uses `urllib.parse/request/error`
  without importing the submodules (8 errors); settings/routes.py and
  settings/utils.py have possibly-unbound variables; ~90 further
  optional-member-access errors across jobs/settings/database/utils.
- Devtools-internal findings from the same run (4 of 5) were fixed in this
  pass; job_service.py:42/83 remain as SQLAlchemy column-typing noise.
- pyright stays an optional tool: not installed by default, `run_type_check`
  returns an install hint, and the install lives in the container only.
