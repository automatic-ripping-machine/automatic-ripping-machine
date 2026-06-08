# Claude Code Project Instructions

## Superpowers Docs Location

Plans, specs, and research for this project live in a **separate private repo**, not in this repo. This keeps AI-collaboration artifacts out of the project history and syncs them across machines.

Expected location: `../arm-ai/<project-subdir>/docs/superpowers/`
  - arm-neu        -> ../arm-ai/arm-neu/docs/superpowers/
  - arm-ui         -> ../arm-ai/arm-ui/docs/superpowers/
  - arm-transcoder -> ../arm-ai/arm-transcoder/docs/superpowers/

When the brainstorming, writing-plans, or executing-plans skills reference `docs/superpowers/specs/...` or `docs/superpowers/plans/...`, resolve those paths against the sibling `arm-ai/` repo above, not this repo.

If the sibling `arm-ai/` directory does not exist, ask the user before creating specs/plans anywhere else. Other developers using this fork should maintain their own equivalent sibling repo.

## Memory

Auto-memory for this repo lives at `../arm-ai/arm-ui/memory/` (start with `MEMORY.md`). Read and write memories there, not in this repo.

## Commit Rules

Engineering standards (branching, PR targets, CI gates, deploy commands) are in `../arm-ai/commit-rules.md` and `../arm-ai/arm-ui/commit-rules.md`. Follow both before committing.
