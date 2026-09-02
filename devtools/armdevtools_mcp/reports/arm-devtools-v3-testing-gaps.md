# ARM-v3 Testing Gap Analysis

Generated 2026-09-02 with the ARM-v3 devtools MCP (`arm-v3-devapi`, 76 tools)
and the jcodemunch structural index of this checkout.

## How this was done, and with what

Three MCP tools were used, each measuring a different layer of the gap:

1. **`jcm_get_untested_symbols`** (jcodemunch structural index). Static
   analysis: the index walks the import graph and symbol references and
   classifies every non-test symbol as *reached* (some test file's import
   chain can reach it) or *untested*. Untested symbols come in two classes:
   `unreached` (no path from any test) and `imported_not_called` (imported by
   something a test reaches, but never called). This is **inferred** from the
   index - it does not execute anything, and results are capped at 100
   symbols (`truncated=true`), so the true untested count is at least what is
   reported.
2. **`find_tests_for_module`** (dev API). The reverse direction: given a
   module name, which test files cover it. Name-based and coarse - it matches
   test-file naming conventions (e.g. `test_ripper_*` files cover
   `arm.ripper.*`), not individual symbols.
3. **`run_coverage`** (dev API). Real executed coverage via pytest-cov. This
   leg currently returns an install hint (`pytest-cov not installed` in the
   container) and, separately, the model-test fixture defects in
   `arm-devtools-v3-bug-notes.md` prevent the full suite from running anyway.
   Until both are fixed, executed coverage is unavailable and this analysis
   rests on the static layer.

## Results

**Headline:** the code has 677 functions and methods. The
index found no evidence of any test reaching at least 100 of them - and that
is a minimum, because the tool stops listing after 100, so the real number
could be higher. Of the 100 listed: 90 are never reached by any test at all,
and 10 are imported by tested code but never actually called.

### By file (untested symbol count)

| File | Untested symbols |
|---|---|
| arm/ripper/main/makemkv.py | 12 |
| arm/ripper/main/identify.py | 10 |
| arm/ripper/main/utils.py | 10 |
| arm/ripper/main/handbrake.py | 9 |
| arm/ripper/main/ARMInfo.py | 8 |
| arm/common/ServerDetails.py | 7 |
| arm/ripper/main/music_brainz.py | 7 |
| arm/ripper/main/arm_ripper.py | 6 |
| arm/models/arm_models.py | 5 |
| arm/ripper/main/main.py | 5 |
| arm/ripper/main/logger.py | 4 |
| arm/config/config.py | 2 |
| arm/config/config_utils.py | 2 |
| arm/models/job.py | 2 |
| arm/models/user.py | 2 |
| arm/models/config.py, notifications.py, system_drives.py, system_info.py, track.py, ui_settings.py | 1 each |
| arm/common/database_manager.py | 1 |
| arm/common/server_ip.py | 1 |
| arm/ripper/main/ProcessHandler.py | 1 |

The gap concentrates in the ripper pipeline (68 of 100) and the models layer.

## Cross-checks with find_tests_for_module

| Module | Test files found |
|---|---|
| arm.ripper.main.utils / handbrake / makemkv | test_ripper/test_ripper_ARMInfo.py, test_ripper/test_ripper_processhandler.py |
| arm.models.job | none |
| arm.common.ServerDetails | none |
| arm.ui.jobs.routes | none |
| arm.ui.devtools.routes | none |

The ripper's two test files exist but cover only ARMInfo/ProcessHandler by
name; the index still marks 68 ripper symbols untested - i.e. the files
exist, but they do not exercise most of the pipeline. The UI layer has no
test files at all under the name-matching convention (the devtools suite
lives under test_ui and covers the dev API, not the ARM UI routes).

## Coverage leg

`run_coverage` cannot run yet: `pytest-cov not installed` in the container,
and the model-test fixtures are broken (see the bug report). When both are
fixed, re-run `run_coverage` to replace the static inference with executed
numbers.

## Interpretation

- The ripper pipeline is the biggest testing gap: makemkv/identify/handbrake/
  utils carry the disc-processing logic users depend on, with almost no test
  reach. A bug there (see the abcde finding in the bug report) ships unseen.
- The models layer is thin on tests but also thin on logic - lower risk.
- The index-derived number is a floor, not a ceiling: the 100-symbol cap and
  the absence of executed coverage both mean the real gap is larger.
- Fix order: repair the model-test fixtures (bug report finding 6), install
  pytest-cov, re-run `run_coverage`, then close gaps starting at the ripper.

## Update 2026-09-02: executed coverage now available

- The coverage leg (`run_coverage`) was tested live after installing
  pytest-cov in the container; the default command needed `--cov=ui`
  (packages are flat in this checkout, so `arm.ui` collected nothing) and
  that fix ships in this change.
- Measured with the devtools suite only: **46% total** (3,473 statements,
  1,866 missed). The devtools layer itself is well covered (routes 86%,
  db_service 93%, test_fixture 97%); the ARM UI routes sit mostly at
  10-27% (jobs/routes 25%, settings/routes 27%, json_api 12%, metadata 10%),
  consistent with the static untested-symbol findings above.
- pytest-cov is optional, not a requirement: absent from the image, and the
  tool returns an install hint until someone runs
  `pip3 install pytest-cov` in the container.
