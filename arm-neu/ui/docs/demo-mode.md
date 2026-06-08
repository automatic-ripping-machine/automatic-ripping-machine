# Demo Mode

Run the ARM UI **standalone, fully populated with sample data** — no ARM ripper
and no Transcoder required. Useful for frontend review, screenshots, and handoff.

When `ARM_UI_DEMO_MODE=true`, the UI backend serves a built-in, deterministic
dataset (jobs, drives, notifications, transcodes, logs, files, posters, etc.)
instead of proxying to the real ARM/Transcoder services. The flag defaults to
`false`, so normal deployments are unaffected.

## Clone → set → run

```bash
# 1. Clone (the contracts submodule is required for the build)
git clone --recurse-submodules https://github.com/uprightbass360/automatic-ripping-machine-ui.git
cd automatic-ripping-machine-ui
# (already cloned without submodules? run: git submodule update --init)

# 2. Set the flag, 3. Run
ARM_UI_DEMO_MODE=true docker compose up --build
```

Then open <http://localhost:8888>.

That's it — the dashboard, job detail, transcoder, settings, notifications,
logs, and file browser all render with sample data and no backend services
running.

## Notes

- **Default is off.** Without `ARM_UI_DEMO_MODE=true` (or with `=false`) the UI
  behaves normally and proxies to ARM (`:8080`) and the Transcoder (`:5000`).
  You can also set it persistently in `docker-compose.yml`
  (`ARM_UI_DEMO_MODE=${ARM_UI_DEMO_MODE:-false}`) or a `.env` file.
- **Port / networking.** The compose service uses `network_mode: host` and
  serves on **8888**. Stop anything already bound to 8888 first.
- **Posters need internet.** Demo posters come from TMDB and Cover Art Archive
  via the UI's image proxy; with no internet the UI falls back to a placeholder.
  Everything else works fully offline.
- **Not hermetic on a host already running ARM/Transcoder.** Any endpoint the UI
  calls that demo mode does not map falls through to the real service if one is
  listening on `:8080`/`:5000`. On a clean host there is nothing to fall through
  to, so the demo is self-contained.
- **Data resets on restart.** Demo state lives in memory; mutations (e.g. pause a
  job, dismiss notifications) persist only for the running session.
