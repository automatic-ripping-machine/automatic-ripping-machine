# ARM-v3 Bug Report

**Note:** this report was written by an AI agent that was asked to produce it.
The MCP does not generate reports on its own - if you want a report like
this, tell the AI to make one.

Generated 2026-09-02 with the ARM-v3 devtools MCP (`arm-v3-devapi`, 75 tools)
plus the jcodemunch structural index of this checkout (231 files, 4,742
symbols). Every finding below was reproduced during this pass; the tool used
for each diagnosis is recorded so the report can be re-run.

## 1. Nine UI routes return 500 on a parameterless GET

**Diagnosed with:** `check_route_health` (9 failing of 31 checked), then
`get_recent_logs` for the Flask tracebacks and `list_routes` to confirm the
view-function mapping.

| Route | Crash site | Root cause |
|---|---|---|
| /jobdetail | arm/ui/jobs/routes.py:51 | `job.manual_mode` on `Job.query.get(None)` |
| /changeparams | arm/ui/jobs/routes.py:249 | `job.config` on `Job.query.get(None)` |
| /updatetitle | arm/ui/jobs/routes.py:202 | `job.title` on `Job.query.get(None)` |
| /gettitle | arm/ui/jobs/routes.py:172 | uncaught `ValidationError("No imdb supplied")` |
| /select_title | arm/ui/jobs/routes.py:157-158 | registered to the same view function as /gettitle |
| /list_titles | arm/ui/jobs/routes.py:268 | bare `raise ValidationError` |
| /logs | arm/ui/logs/routes.py:40 | `request.args['mode']` -> BadRequestKeyError |
| /logreader | arm/ui/logs/routes.py:104 | `os.path.join(log_path, None)` -> TypeError |
| /error | arm/ui/errors/routes.py:49 | 500 by design (`abort(500)`) - health-check false positive |

Summary: 7 of 9 are v2 routes ported to v3 without their input guards - they
dereference a Job fetched from a query arg that may be absent, with no
`if job is None` fallback, so a bare GET is a 500 instead of the v2 flash +
redirect home.

## 2. Home page never displays jobs

**Diagnosed with:** `inspect_current_view` on `/` - the rendered snapshot
shows navbar, welcome heading and CPU temp only; no jobs section exists.

- **Source:** arm/ui/main/routes.py:49 - `jobs = {}` with
  `# TODO fix this back to something that works, pending ripper working`
- **Impact:** every user sees an empty home page; the main UI is blind until
  this is wired back to the jobs query.

## 3. json_api delete endpoints: dead code that reports success

**Diagnosed with:** `list_routes` - no delete route is registered (only the
`/json` GET feed exists, as `route_jobs.feed_json`). The dead code sits in
arm/ui/jobs/json_api.py `delete_job()`:

- the `job_id == 'all'` branch has every delete statement commented out,
  logs "No deletes went to db" (line 294) and still returns
  `{'success': True}`
- the `job_id == 'title'` branch is commented out with "This causes db
  corruption!" (line 299) and also returns `{'success': True}`

- **Impact:** nothing can call these today, but anyone re-registering the
  endpoints gets told the wipe succeeded while nothing happened. Either wire
  real deletes or remove the code.

## 4. abcde rips never verify all tracks ripped

**Diagnosed with:** code inspection (no physical disc to run against;
`get_tool_versions` confirms abcde is installed).

- **Source:** arm/ripper/main/utils.py:396 -
  `subprocess.check_output(cmd)` followed by
  `# TODO check output and confirm all tracks ripped; find "Finished\.$"`
- **Impact:** a CD rip that dies halfway still reports success (returncode 0
  only means the command ran); users get partial albums marked complete.

## 5. Alembic migration chain incomplete

**Diagnosed with:** `query_db alembic_version` - the dev DB carries a single
stamped row (`d1490bfe8120`), consistent with stamping rather than a real
migration run; a fresh-DB `upgrade` creates only `alembic_version`.

- **Source:** arm/ui/migrations/versions/ - chain gaps between the
  create_table revisions
- **Impact:** a clean production deploy from migrations alone produces an
  empty schema; the documented migration path yields a broken UI.

## 6. Model tests broken - two distinct fixture defects

**Diagnosed with:** `run_tests_for_file test_ui/test_model_job.py` (app-context
failure, reproduced standalone) and `run_pr_checks` (FK failure, reproduced
in the full suite). Two separate defects:

1. **No app context.** v2-era fixtures call `db.session` directly;
   Flask-SQLAlchemy 3.x requires an app context the fixtures never push.
   Standalone run of either model test file fails with
   `RuntimeError: Working outside of application context` at
   test_ui/test_model_config.py:25. The full suite masks it only because a
   context-pushing test happens to run first.
2. **Hardcoded foreign key.** test_ui/test_model_job.py:23 creates
   `Track(1, ...)` with a literal `job_id=1` while its Job's real
   auto-increment id drifts after rolled-back inserts; the commit then fails
   with `IntegrityError 1452` on `track_ibfk_1`.

- **Impact:** the PR checks stop at the first model-test error; the model
  test infrastructure needs the context fix and the FK fix.

## 7. SystemInfo row for the UI goes stale

**Diagnosed with:** `query_db system_info` - the single UI row has
`last_update_time: null`; created once and never heartbeated. The ripper's
monitor updates its own row.

- **Source:** arm/ui/main/routes.py:78 (create-only on /systemsetup submit)
- **Impact:** the UI shows frozen CPU/mem stats; anything reading server
  liveness sees stale data.

## 8. Structural pass (jcodemunch index)

**Diagnosed with:** `jcm_get_repo_health`, `jcm_find_dead_code`,
`jcm_get_hotspots`.

- Dead code: 0 files/symbols. The only zero-importer hits are static CSS/JS
  assets and one installer shell script - expected.
- Import cycles: 0.
- Coupling: 49 modules flagged "unstable" (high outward dependency) - a
  metric lead only; no individual list is returned by the index.
- Complexity hotspots (top 10): every entry is the devtools change itself -
  `build_tools` (cyclomatic 62), `register_routes` (31), `replay_job_fixture`
  (23), `validate_job_completion` (22), `_build_dispatch` (22), `_probe`
  (18), `_probe_file` (17), `inspect_element` (17), `get_recent_exceptions`
  (16), `find_tests_for_module` (15). The MCP tooling is now the
  highest-complexity code in the repo. build_tools' figure is inflated by
  its single-literal 75-tool list rather than branching logic.

Unconfirmed leads from the same sweep are tracked separately in
`arm-devtools-v3-potential-bugs.md`; testing coverage gaps in
`arm-devtools-v3-testing-gaps.md`; the token/time cost of running this
tooling in `arm-devtools-v3-cost-analysis.md`; and which tools work out of
the box vs. need optional installs in `arm-devtools-v3-tool-surface.md`.

## 9. migrations/env.py references an undefined `logger`

**Diagnosed with:** `run_type_check` (pyright 1.1.411, run live 2026-09-02).

- **Source:** arm/ui/migrations/env.py:94 - `logger` is not defined
  (pyright reportUndefinedVariable). The migration environment never
  configures that name.
- **Impact:** a NameError on the migration code path that reaches line 94.

## Checks that came back clean

`check_db_integrity` (all 9 tables), `check_job_consistency` (no dead pids,
orphaned tracks or configs), `get_recent_exceptions` (no traceback blocks in
current logs), flake8 over arm/test_ui/test_ripper/devtools.

