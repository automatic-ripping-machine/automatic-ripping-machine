# Automatic Ripping Machine (ARM) - Development Tools

Development tooling for ARM v3: a JSON API inside the ARM UI for inspecting and
driving the application, plus a server that lets AI coding assistants use it.

If you are new to the AI side of this, four concepts cover everything below:

- **AI coding assistant (agent).** A program you talk to that reads, writes
  and runs code - Claude Code, Cursor, Copilot, Codex and similar. It works by
  calling *tools*: small programs or APIs that do one job and report back.
- **MCP (Model Context Protocol).** The standard plug for giving agents tools.
  An MCP server is a program that publishes a list of tools; any agent that
  speaks MCP can connect to it, regardless of vendor. Write the tools once and
  every agent gets them - that is the whole reason this project ships an MCP
  server.
- **uv.** A package manager for Python. One `uv tool install` command installs
  a program together with all its Python dependencies in an isolated
  environment - no manual virtualenv or pip steps.
- **Index.** Agents have a limited working memory, so reading whole files is
  expensive. An index is a precomputed map of the code or docs that lets the
  agent ask for exactly the piece it needs instead.

The design keeps two halves strictly separate:

- The **developer JSON API** runs inside ARM (a Flask blueprint gated by
  `ENABLE_DEVTOOLS`). Anything can call it - curl, scripts, agents. It is the
  half that knows ARM's internals.
- The **MCP server** is a standalone program that calls that API over plain
  HTTP. It imports nothing from ARM, so it cannot break the app and the app
  cannot break it.

## Developer JSON API

The ARM UI exposes a dev-gated JSON API at `/__devtools`. It is disabled by
default; enable it in arm.yaml (the template entry lives in `setup/arm.yaml`):

```yaml
ENABLE_DEVTOOLS: true
```

then restart the ARM UI. Every response uses a stable envelope:

```json
{"success": true, "timestamp": "...", "errors": [], "data": {...}}
```

Endpoint groups: `/state`, `/logs`, `/routes`, `/db`, `/describe-model`,
`/db/table-counts`, `/config`, `/config/value`, `/system/tool-versions`,
`/system/disk-space`, `/system/processes`, `/system/config-paths`,
`/job/<id>`, `/jobs/by-status`, `/jobs/recent`, `/job/<id>/export`,
`/job/<id>/tracks`, `/tracks/orphaned`, `/job/<id>/reset`, `/job/<id>/update`,
`/job/<id>/abandon`, `DELETE /job/<id>`, `/jobs/delete`, `/jobs/delete-all`,
`/jobs/clean`, `/reset-all`, `/track/<id>/reset`, `/fixtures/job`,
`/fixtures/track`, `/view`, `/inspect-element`, `/find-element`, `/reload`,
`/compare`, `/exec/tests`, `/exec/find-tests`, `/exec/run-for-file`,
`/exec/lint`, `/exec/coverage`, `/exec/integrity`, `/tools/mutations`,
`/bugs/db-integrity`, `/bugs/job-consistency`, `/bugs/route-health`,
`/bugs/type-check`, `/request`.

Destructive endpoints (`delete_job`, `delete_jobs`, `delete_all_jobs`,
`clean_jobs`, `reset_all`) honour a `dry_run` flag from the JSON body or query
string. `list_tool_mutations` classifies every tool read_only / mutating /
destructive - check it before calling.

Example:

```bash
curl -s http://127.0.0.1:8080/__devtools/state
```

## MCP server

The devtools directory is an installable package (see `devtools/pyproject.toml`)
that provides the `arm-devtools-mcp` command: an MCP server over the developer
API. It also carries host-side tools the legacy CLI used to do:
`docker_compose_build` (rebuild + restart the stack), `docker_compose_restart`,
and `run_pr_checks` (git submodule update, flake8, pytest).

### Install

Requires [uv](https://docs.astral.sh/uv/). From inside a checkout of this
repository:

```bash
uv tool install ./devtools
```

Or install directly from the repository, with no checkout at all - the
`#subdirectory=devtools` part points at the directory the package lives in
(this form works once the devtools change is merged into the repository):

```bash
uv tool install "git+https://github.com/automatic-ripping-machine/automatic-ripping-machine.git#subdirectory=devtools"
```

Either way `arm-devtools-mcp` ends up on PATH with its dependencies resolved
automatically. To run without installing, straight from a checkout:

```bash
uvx --from ./devtools arm-devtools-mcp --base-url http://127.0.0.1:8080
```

`--base-url` points at the ARM UI (default `http://127.0.0.1:8080`).

### Register with an AI coding assistant

The server is a single command, so any MCP-capable assistant registers it the
same way - one entry in its config listing the command to launch:

```json
{
  "mcpServers": {
    "arm-v3-devapi": {
      "command": "arm-devtools-mcp",
      "args": ["--base-url", "http://127.0.0.1:8080"]
    }
  }
}
```

For example, Claude Code:

```bash
claude mcp add --scope project arm-v3-devapi -- arm-devtools-mcp --base-url http://127.0.0.1:8080
```

Good first tools to call in any session: `get_app_state` (what ARM is doing
right now), `list_tool_mutations` (read_only/mutating/destructive map),
`get_tool_errors` (genuine failures from earlier calls). Genuine tool failures
are appended to `devapi_errors.log` next to the server (bounded, redacted);
start every session by checking them.

### Tool reference

The full tool surface, grouped. `list_tool_mutations` gives the authoritative
read_only / mutating / destructive classification for any of them; the tier
split (works out of the box / degrades honestly / needs an optional install)
is annotated in `armdevtools_mcp/reports/arm-devtools-v3-tool-surface.md`.

- **State & logs** (4): `get_app_state`, `get_recent_logs`, `list_routes`,
  `get_tool_errors`
- **Log analysis** (4): `get_logs_for_job`, `search_logs`, `get_log_stats`,
  `get_recent_exceptions`
- **Database** (4): `query_db`, `describe_model`, `get_table_counts`,
  `get_db_status`
- **Config & system** (7): `get_app_config`, `get_config_value`,
  `set_config_value` (mutating, in-memory only - lost on restart),
  `get_tool_versions`, `check_disk_space`, `get_process_list`,
  `get_config_paths`
- **Jobs - read** (8): `get_job`, `get_jobs_by_status`, `get_recent_jobs`,
  `export_job_as_json`, `get_job_tracks`, `find_orphaned_tracks`,
  `list_job_outputs`, `validate_job_completion`
- **Jobs - mutate** (9): `reset_job_status`, `update_job`, `abandon_job`,
  `reset_track_state`, `reset_all`; destructive with dry_run support:
  `delete_job`, `delete_jobs`, `delete_all_jobs`, `clean_jobs`
- **Test fixtures** (2): `create_test_job`, `insert_test_track`
- **Media & metadata** (3): `probe_media_file`, `test_metadata_lookup`,
  `replay_job_fixture` (mutating)

Note: `probe_media_file` runs ffprobe inside the UI container; the v3 image
does not ship ffmpeg, so install it first (e.g. `apt-get install ffmpeg`) or
the probe reports `probe_failed` honestly.
- **UI inspection** (5): `inspect_current_view`, `inspect_element`,
  `find_element_by_text`, `reload_dev_view`, `compare_view_states`
- **Dev loop** (6): `run_tests`, `run_tests_for_file`, `find_tests_for_module`,
  `run_linter`, `run_coverage`, `check_test_integrity`
- **Bugs, audit & proxy** (6): `list_tool_mutations`, `check_db_integrity`,
  `check_job_consistency`, `check_route_health`, `run_type_check`,
  `make_http_request`
- **Host-side** (3): `docker_compose_build`, `docker_compose_restart`,
  `run_pr_checks`
- **External MCP gateway** (4): `mcp_external_servers`, `mcp_external_tools`,
  `mcp_external_call`, `mcp_external_health`
- **jCodeMunch code intelligence** (11, wrappers over the gateway):
  `jcm_search_symbols`, `jcm_get_symbol_source`, `jcm_get_file_outline`,
  `jcm_get_call_hierarchy`, `jcm_find_dead_code`, `jcm_get_blast_radius`,
  `jcm_get_hotspots`, `jcm_check_edit_safe`, `jcm_get_repo_health`,
  `jcm_get_repo_map`, `jcm_get_untested_symbols` (testing-gap analysis)

These are native tools that forward to the jcodemunch index (structural
queries: dead code, callers, blast radius, hotspots). They are on by default
and report `not-installed` honestly when jcodemunch is absent - same
conditional behaviour as the gateway tools.

### External MCP servers

Some jobs are better done by specialised tools than by hand-rolled scripts.
Two of them, jcodemunch and jdocmunch, keep indexes: jcodemunch indexes your
code (symbols, references, callers), jdocmunch indexes documentation (sections
of docs instead of whole files). git provides repository operations (status,
diff, log, branches), and pyright provides type-level code intelligence
(definitions, references, diagnostics).

The MCP server acts as a gateway to these: four tools (`mcp_external_servers`,
`mcp_external_tools`, `mcp_external_call`, `mcp_external_health`) list them,
list their tools, forward calls and check their health. The list of servers
lives in `devtools/armdevtools_mcp/external_mcp.json`.

Every external server is optional: with none of them installed the MCP and the
`/__devtools` HTTP API work exactly as before, and the gateway tools report
`not-installed` status. To use them, install any subset:

```bash
uv tool install jcodemunch-mcp
uv tool install jdocmunch-mcp
uv tool install mcp-server-git
uv tool install jons-mcp-pyright
```

The gateway tools are an MCP-layer feature - the `/__devtools` HTTP API is
untouched and requires no external tools.

Semantics:

- Every forwarded call starts a **fresh server process** - the external
  server's session state does not persist between calls (startup cost roughly
  0.5-4s; tool lists are cached for 30s).
- A missing server reports `not-installed` - honest, never fatal. Integration
  is deliberately conditional on the tools existing.
- Each server config has `deny_patterns`: tool names containing these words
  (e.g. `invalidate` on jcodemunch, `reset`/`init` on git) are refused before
  anything runs. These are index-destroying or setup tools an agent should
  never call unattended.
- Results are truncated to 20,000 chars; call timeout defaults to 120s
  (1-600s overridable). Genuine failures land in devapi_errors.log as usual.
- The mcp SDK starts children with a minimal environment; servers that need
  more (API keys, XDG dirs) declare it in their config `env`.
- Forwarded output is length-truncated only, not secret-redacted.

### Keeping indexes and tools current

An index is a snapshot: jcodemunch and jdocmunch answer from whatever was on
disk the last time they indexed. Edit code or docs, and their answers go
stale until the indexer runs again. So re-index after making changes, using
each server's own index tools through the gateway (find them with
`mcp_external_tools`, then drive them with `mcp_external_call`). In
agent-based workflows this is automated: the agent's instructions tell it to
re-index after edits, so stale answers never happen in practice.

The same instructions ask the agent to log gaps: when a task needs a
capability the tool set does not have, the agent writes the gap down (session
notes or `devapi_errors.log`) instead of silently working around it. Those
logged gaps are periodically turned into new devapi tools, growing the MCP
from real usage.

Why this cycle helps: the indexes stay accurate without human bookkeeping;
the tool set is extended from observed need rather than guesswork; and every
agent session doubles as requirements-gathering for the MCP itself.

### What is not included (and why)

Not every capability of the previous (v2) devtools is in this change. The full
accounting:

- **Ported from v2.** The bulk of the tool surface, plus the log-analysis,
  job-output/completion, media-probe, metadata-test and fixture-replay tools
  listed above.
- **Superseded, not ported.** The v2 explain/diagnose tools were hardcoded
  natural-language templates over ARM state; with an agent in the loop,
  explanation is the agent's own job over `get_app_state`, so porting them
  would add stale boilerplate. The v2 Playwright read-side tools
  (`capture_page_activity`, `get_computed_styles`, `monitor_page_refresh`,
  `evaluate_script`) are covered by the server-side snapshot tools without a
  live browser session - and `evaluate_script` ran arbitrary JS inside the UI
  session, which the snapshots never need.
- **Blocked on missing v3 pieces.** `compare_job_progress`,
  `compare_dashboard_drive_state` and `get_dashboard_data` need the v3
  dashboard, which is still a stub in the UI (see the bug report);
  `populate_tv_cache` needs the TV season/episode models that v3 does not
  have. These port when v3 grows the underlying pieces.
- **Held back.** Browser actuation (`navigate_to`, `click_element`,
  `screenshot`): a click on the live ARM UI has no dry_run - it can eject a
  disc, delete a job or change settings, and nothing in the toolset can
  preview it. Read-only snapshots are the safe surface for an agent;
  actuation stays out unless deliberately added.

Any skipped tool can be added later by asking an agent to port it - the
gap-logging cycle above is the on-ramp for exactly that.

## Dev stack

Dev environment for this checkout (UI on 8081, DBs on 3307/3308, data under
`./dev-data`):

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d arm-db arm-ui
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d arm-db-test   # for test_ui
```

## Tests

The devtools suite against the test DB (runs inside the arm-ui container):

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml run --rm -w /opt/arm \
    -e FLASK_ENV=testing -e MYSQL_IP=arm-db-test arm-ui \
    python3 -m pytest test_ui/test_bp_devtools.py -v
```

The MCP layer, host-side (uv supplies pytest to the package environment):

```bash
cd devtools
uv run --with pytest pytest tests/test_external_mcp.py -v
```

Fake-server tests always run; real-server handshakes skip when a binary is
absent. Container pytest skips the module via `importorskip("mcp")`.

Known test-suite state: `test_ui/test_bp_devtools.py` is green. The
pre-existing model tests error on setup (Flask-SQLAlchemy 3.x requires an app
context their fixtures never push) and with PendingRollback errors -
`run_pr_checks` reports those honestly until the v3 test infra is fixed.

Optional legs (verified live 2026-09-02, not requirements): `run_type_check`
(pyright) and `run_coverage` (pytest-cov) return an install hint until their
tool is present. To enable them in the container:

```bash
docker exec arm-ui pip3 install "pyright[nodejs]" pytest-cov
```

The install is per-container (lost on image rebuild); adding the packages to
the UI image is the durable option, and is not part of this change.

## Legacy CLI scripts and overlap

The pre-v3 scripts in this directory (`armdevtools.py`, `armdocker.py`,
`armgit.py`, `armui.py`, `database.py`, `log.py`, `pytest_ui.py`) are left
untouched and remain the supported path for humans at a terminal. Some of
their jobs overlap with the MCP tools on purpose:

| Legacy function | Overlapping MCP tool | Relationship |
|---|---|---|
| `armdocker.docker_rebuild` / `dockercompose_rebuild` | `docker_compose_build`, `docker_compose_restart` | same jobs, reimplemented host-side |
| `armgit.pr_update()` (submodule update, flake8, pytest) | `run_pr_checks` | same sequence, reimplemented host-side |
| `armgit.flake8()` | `run_linter` | lint now runs inside the arm-ui container |
| `pytest_ui.ui_test()` | `run_tests`, `run_tests_for_file` | tests now run inside the container against the test DB |
| `database.database_backup()` | - | dropped: v2 was SQLite (a file copy); v3 is MySQL, and `get_db_status`/`check_db_integrity` cover inspection. A mysqldump-based backup tool could be added if needed. |

Why the overlap exists:

- The legacy scripts were written for a human at a console: they print text
  and expect a person to read it. An agent needs the opposite - structured
  results (the `{"success": ..., "errors": ...}` envelope), a machine-readable
  record of failures (`devapi_errors.log`), and dry_run flags it can check
  before anything destructive. The MCP tools run the same underlying
  operations and return results an agent can act on.
- They are container-aware. The legacy scripts assume a bare-metal install;
  the MCP equivalents know the compose layout, run lint and tests inside the
  arm-ui container, and target arm-db-test instead of a live database.
- Keeping both means nobody's workflow breaks: humans keep the CLIs, agents
  get the MCP, and the shared operations (docker, git, flake8, pytest) are
  the same ground truth either way.
- `database_backup` is the exception: it backed up the v2 SQLite file, which
  does not exist in v3, so there was nothing to port - it was dropped rather
  than overlapped.

## Troubleshooting

Please see the [wiki](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/).

## Contributing

Pull requests are welcome.  Please see the [Contributing Guide](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/Contributing-Guide)

If you set ARM up in a different environment (hardware/OS/virtual/etc.), please consider submitting a howto to the [wiki](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki).

## License

[MIT License](../LICENSE)
