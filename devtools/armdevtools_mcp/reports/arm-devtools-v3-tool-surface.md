# ARM-v3 Devtools Tool Surface

Which of the MCP's 76 tools work out of the box, which degrade honestly
until something optional is installed, and which appear only as wrappers
over optional external servers. Generated 2026-09-02 from the shipped
`TOOL_REGISTRY` and `external_mcp.json`.

## Tier 1 - Vanilla MCP: always available, no external dependency (54)

These are backed by the in-app developer API and work the moment
`ENABLE_DEVTOOLS` is on. Nothing extra to install.

- **State & logs** (4): `get_app_state`, `get_recent_logs`, `list_routes`,
  `get_tool_errors`
- **Log analysis** (4): `get_logs_for_job`, `search_logs`, `get_log_stats`,
  `get_recent_exceptions`
- **Database** (4): `query_db`, `describe_model`, `get_table_counts`,
  `get_db_status`
- **Config & system** (7): `get_app_config`, `get_config_value`,
  `set_config_value`, `get_tool_versions`, `check_disk_space`,
  `get_process_list`, `get_config_paths`
- **Jobs - read** (8): `get_job`, `get_jobs_by_status`, `get_recent_jobs`,
  `export_job_as_json`, `get_job_tracks`, `find_orphaned_tracks`,
  `list_job_outputs`, `validate_job_completion`
- **Jobs - mutate** (9): `reset_job_status`, `update_job`, `abandon_job`,
  `reset_track_state`, `reset_all`, `delete_job`, `delete_jobs`,
  `delete_all_jobs`, `clean_jobs`
- **Test fixtures** (2): `create_test_job`, `insert_test_track`
- **Media & metadata** (1): `replay_job_fixture`
- **UI inspection** (5): `inspect_current_view`, `inspect_element`,
  `find_element_by_text`, `reload_dev_view`, `compare_view_states`
- **Dev loop** (5): `run_tests`, `run_tests_for_file`,
  `find_tests_for_module`, `run_linter`, `check_test_integrity`
- **Bugs, audit & proxy** (5): `list_tool_mutations`, `check_db_integrity`,
  `check_job_consistency`, `check_route_health`, `make_http_request`

## Tier 2 - Vanilla tools that degrade honestly (11)

Always in the tool list, never a hard failure - each returns an install hint
or a `not-installed`/`probe_failed` status until its dependency exists.

| Tool | Needs | Without it |
|---|---|---|
| `run_type_check` | pyright in the container | returns the install hint |
| `run_coverage` | pytest-cov in the container | returns the install hint |
| `probe_media_file` | ffprobe in the container | `probe_failed` per file |
| `test_metadata_lookup` | OMDB/TMDB API key in arm.yaml | honest no-key report |
| `docker_compose_build` / `docker_compose_restart` / `run_pr_checks` | docker on the host | `not found on this machine` |
| `mcp_external_servers` / `mcp_external_tools` / `mcp_external_call` / `mcp_external_health` | the external servers listed below | `not-installed` status |

## Tier 3 - Additional tools, present only if jCodeMunch is installed (11)

Wrappers over the jcodemunch code index. They are listed by default and
report `not-installed` when jcodemunch is absent; install it with
`uv tool install jcodemunch-mcp` and they work with no further setup (the
checkout's repo id is injected automatically).

`jcm_search_symbols`, `jcm_get_symbol_source`, `jcm_get_file_outline`,
`jcm_get_call_hierarchy`, `jcm_find_dead_code`, `jcm_get_blast_radius`,
`jcm_get_hotspots`, `jcm_check_edit_safe`, `jcm_get_repo_health`,
`jcm_get_repo_map`, `jcm_get_untested_symbols`

## Verification notes

- The tier split was generated from the shipped code: 76 total = 54 + 11 + 11.
- `run_type_check` and `run_coverage` were exercised live on 2026-09-02
  (pyright 125 errors across arm/ui; coverage 46% total) - the tier-2
  install hints are their only default behavior.
- The jcm wrappers were exercised live against the indexed checkout
  (4,755 symbols).
