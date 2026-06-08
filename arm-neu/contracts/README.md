[![CI](https://github.com/uprightbass360/automatic-ripping-machine-contracts/actions/workflows/test.yml/badge.svg)](https://github.com/uprightbass360/automatic-ripping-machine-contracts/actions/workflows/test.yml)
[![GitHub release](https://img.shields.io/github/v/release/uprightbass360/automatic-ripping-machine-contracts)](https://github.com/uprightbass360/automatic-ripping-machine-contracts/releases/latest)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

# arm-contracts

Part of the [Automatic Ripping Machine (neu) ecosystem](#related-projects). Shared Pydantic models for the cross-service wire contract between the ripper, the UI dashboard, and the GPU transcoder.

Consumer repos pull this in as a git submodule at `components/contracts` and install it editable (`pip install -e components/contracts`). A CI gate in each consumer enforces that the submodule points at this repo's `main` tip, and an auto-bump workflow opens a PR on each consumer when `main` advances here — so the three services stay in lockstep with a single source of truth for the wire format.

## Related Projects

Part of the Automatic Ripping Machine (neu) ecosystem:

| Project | Description |
|---------|-------------|
| [automatic-ripping-machine-neu](https://github.com/uprightbass360/automatic-ripping-machine-neu) | Fork of the original ARM with bug fixes and improvements |
| [automatic-ripping-machine-ui](https://github.com/uprightbass360/automatic-ripping-machine-ui) | Modern replacement dashboard (SvelteKit + FastAPI) |
| [automatic-ripping-machine-transcoder](https://github.com/uprightbass360/automatic-ripping-machine-transcoder) | GPU-accelerated transcoding service |
| **automatic-ripping-machine-contracts** | Typed shared-contracts layer keeping the services in lockstep (this project) |

The original upstream project: [automatic-ripping-machine/automatic-ripping-machine](https://github.com/automatic-ripping-machine/automatic-ripping-machine)

## What's in here

Pydantic v2 models, exported from `arm_contracts`:

- `job` / `job_config` — the job record passed from ripper to transcoder, plus per-job preset/encoder overrides
- `track` — per-title track metadata (runtime, language, audio/subtitle streams)
- `progress` — phase-aware progress payload (rip / copy / transcode / finalize) with `copy_progress` + `copy_stage`
- `rsync` — shared rsync stdout parser and tracker used by the copy phase
- `webhook` / `callback` — request/response shapes for ripper→transcoder webhooks and transcoder→ripper callbacks
- `media_metadata` + `PATTERN_TOKENS` — metadata fields and the token map used for filename templating
- `expected_title` — TVDB episode-matching hints
- `overrides` — named-file and per-job override schema
- `enums` — shared enum types (job status, disc type, encoder, etc.)
- `notification_event` — discriminated union of job lifecycle events (`job.started`, `job.rip_complete`, `job.transcode_complete`, `job.failed`)
- `notification_channel` — channel config union (Apprise / Webhook / Bash), plus `Channel`, `ChannelCreate`, `ChannelUpdate`, `ChannelTemplate`, `EVENT_KEYS`
- `outbound_webhook_payload` — `OutboundWebhookPayload`, the v18 rich-payload wire shape for user-configured webhook channels

## Versioning

Semantic versioning, with releases cut by [release-please](https://github.com/googleapis/release-please). See [CHANGELOG.md](CHANGELOG.md) for the full history and breaking-change notes.

Wire-format breaking changes bump the major version. Consumers are pinned by submodule SHA, so a major bump here doesn't break a deployment until the consumer's auto-bump PR is merged.

## License

MIT — see [LICENSE](LICENSE).
