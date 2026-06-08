# Changelog

## [4.1.0](https://github.com/uprightbass360/automatic-ripping-machine-contracts/compare/v4.0.0...v4.1.0) (2026-05-26)


### Features

* **notifications:** add optional fields map to AppriseChannelConfig ([3c73257](https://github.com/uprightbass360/automatic-ripping-machine-contracts/commit/3c732572ab4bf0fcff5f94eec4c0e9f92f1e8b71))
* **notifications:** add optional service_id to AppriseChannelConfig ([c86a87d](https://github.com/uprightbass360/automatic-ripping-machine-contracts/commit/c86a87d437ccd3339d7a9ac3e9c8540cf1b1356e))

## [4.0.0](https://github.com/uprightbass360/automatic-ripping-machine-contracts/compare/v3.2.0...v4.0.0) (2026-05-19)


### ⚠ BREAKING CHANGES

* **notifications:** Adds new required Pydantic models. Consumers (arm-neu, arm-ui) must pin the contracts submodule to v4.x and use the new NotificationEvent / Channel / OutboundWebhookPayload types. The actual notification dispatch code in neu and the UI page that uses it land in sub-spec 2 and sub-spec 3.

### Features

* **notifications:** add Channel / ChannelCreate / ChannelUpdate ([3da9215](https://github.com/uprightbass360/automatic-ripping-machine-contracts/commit/3da9215a61cf188c132d4f78d3b8273078ccedb8))
* **notifications:** add channel JSON fixtures + round-trip tests ([f6e3ed5](https://github.com/uprightbass360/automatic-ripping-machine-contracts/commit/f6e3ed5b4254acf24823153ccedf2b39682285c4))
* **notifications:** add ChannelConfig discriminated union ([b3322fc](https://github.com/uprightbass360/automatic-ripping-machine-contracts/commit/b3322fc4d1184ed5e54909aa49ea3457b2542f5f))
* **notifications:** add event JSON fixtures + round-trip tests ([ea1b5c0](https://github.com/uprightbass360/automatic-ripping-machine-contracts/commit/ea1b5c0c4a881b8c1930a49d67271ee1433cc9ee))
* **notifications:** add EVENT_KEYS, ChannelTemplate, public re-exports ([ffcaa6d](https://github.com/uprightbass360/automatic-ripping-machine-contracts/commit/ffcaa6d52da58b7ef34b0f133e1f053ec0f323e1))
* **notifications:** add four concrete event types ([d9d7e3b](https://github.com/uprightbass360/automatic-ripping-machine-contracts/commit/d9d7e3b6ff7c55fe18af1e2081496a89692db6b1))
* **notifications:** add JobEventBase for event payloads ([ff8805f](https://github.com/uprightbass360/automatic-ripping-machine-contracts/commit/ff8805f70a8284ee22d30213999f3c4d7c10bdc5))
* **notifications:** add manual_wait_required and duplicate_detected events ([4e1146b](https://github.com/uprightbass360/automatic-ripping-machine-contracts/commit/4e1146b7f6e24af991be22ccdee3c6ec92262578))
* **notifications:** add NotificationEvent discriminated union ([3547c9c](https://github.com/uprightbass360/automatic-ripping-machine-contracts/commit/3547c9c16bf87ddea50ffeae8fc2cfc852cbcb5e))
* **notifications:** add outbound webhook payload fixture + snapshot ([fbc1d21](https://github.com/uprightbass360/automatic-ripping-machine-contracts/commit/fbc1d21cc5e756ad7daad4e65df6020a2c784323))
* **notifications:** add OutboundWebhookPayload + ChannelRef ([bb8c39b](https://github.com/uprightbass360/automatic-ripping-machine-contracts/commit/bb8c39bdbd8d15e3bf7888a5f225b38e06fab8e2))
* **notifications:** introduce notification events, channels, outbound payload ([f16a729](https://github.com/uprightbass360/automatic-ripping-machine-contracts/commit/f16a72916cbfa03811ad7c96e62909fead90b3ca))


### Bug Fixes

* **notifications:** restore case-sensitive ordering of __all__ ([cbf6e9f](https://github.com/uprightbass360/automatic-ripping-machine-contracts/commit/cbf6e9f093b388971da379cd1620fc4e24397177))

## [3.2.0](https://github.com/uprightbass360/automatic-ripping-machine-contracts/compare/v3.1.0...v3.2.0) (2026-05-11)


### Features

* add MediaMetadata contract + PATTERN_TOKENS map ([cbb91a7](https://github.com/uprightbass360/automatic-ripping-machine-contracts/commit/cbb91a7f2122d893cb9f21cbe0038297672a4ed0))
* re-export MediaMetadata + PATTERN_TOKENS from package root ([b9be9d9](https://github.com/uprightbass360/automatic-ripping-machine-contracts/commit/b9be9d94cd103aab0f7a892b817df653fd974746))

## [3.1.0](https://github.com/uprightbass360/automatic-ripping-machine-contracts/compare/v3.0.0...v3.1.0) (2026-05-09)


### Features

* **progress:** add copy_progress and copy_stage fields ([781d527](https://github.com/uprightbass360/automatic-ripping-machine-contracts/commit/781d527cfc7743a5580d748f60dbac99a340ad92))
* **rsync:** add shared progress parser and tracker ([48422cc](https://github.com/uprightbass360/automatic-ripping-machine-contracts/commit/48422cc547752c1fdd02fc3ebc7ff1835facea5c))


### Bug Fixes

* **rsync:** spread conformance payload across multiple files ([307bef8](https://github.com/uprightbass360/automatic-ripping-machine-contracts/commit/307bef89f1398c3525a74292d89b6e83acb06cfa))
* **rsync:** tighten filename heuristic + clean up review nits ([d6fda43](https://github.com/uprightbass360/automatic-ripping-machine-contracts/commit/d6fda435b4931f522b7372a90739dfbcf01c5d83))

## [3.0.0](https://github.com/uprightbass360/automatic-ripping-machine-contracts/compare/v2.1.0...v3.0.0) (2026-05-07)


### ⚠ BREAKING CHANGES

* WebhookPayload.folder_name and WebhookPayload.path are removed; WebhookTrackMeta.folder_name is removed. Producers must send input_path and output_path on every job-bound webhook. Consumers must read the new fields. See spec docs/superpowers/specs/2026-05-07-webhook-input-output-paths-design.md in the arm-neu sibling AI repo.

### Features

* add input_path/output_path to WebhookPayload, drop folder_name/path ([37d3fd4](https://github.com/uprightbass360/automatic-ripping-machine-contracts/commit/37d3fd4e166b61ebf31ed08a3bde5f368f9ba413))

## [2.1.0](https://github.com/uprightbass360/automatic-ripping-machine-contracts/compare/v2.0.0...v2.1.0) (2026-05-04)


### Features

* **enums:** add SourceType.iso ([de4062c](https://github.com/uprightbass360/automatic-ripping-machine-contracts/commit/de4062cd7cce03a08fa6ebfdf1419da0be50736f))

## [2.0.0](https://github.com/uprightbass360/automatic-ripping-machine-contracts/compare/v1.0.0...v2.0.0) (2026-05-02)


### ⚠ BREAKING CHANGES

* **enums:** JobState members previously aliased onto shared wire strings are now distinct. Renames:   VIDEO_RIPPING       'ripping'  -> 'video_ripping'   AUDIO_RIPPING       'ripping'  -> 'audio_ripping'   MANUAL_WAIT_STARTED 'waiting'  -> 'manual_paused' (member renamed to MANUAL_PAUSED)   VIDEO_WAITING       'waiting'  -> 'makemkv_throttled' (member renamed to MAKEMKV_THROTTLED)

### Features

* **enums:** disambiguate JobState aliases; add TrackStatus.failed ([f25f31e](https://github.com/uprightbass360/automatic-ripping-machine-contracts/commit/f25f31e8d1b7a0a70ead226eb2598c4eee6d9b40))

## [1.0.0](https://github.com/uprightbass360/automatic-ripping-machine-contracts/compare/v0.6.0...v1.0.0) (2026-05-02)


### ⚠ BREAKING CHANGES

* **webhook:** WebhookPayload.type is now WebhookEventType | None rather than free str. Producers must send 'info' (only current member); the enum closes the contract so future event types are explicit breaking changes rather than silent typos.

### Features

* **enums:** add JobState, SourceType, TrackStatus, WebhookEventType, SkipReason ([a499c9a](https://github.com/uprightbass360/automatic-ripping-machine-contracts/commit/a499c9ab168cd56195b1a4cf45a9ba9ef4f0bafb))
* **webhook:** type field is now WebhookEventType enum ([6ee32b6](https://github.com/uprightbass360/automatic-ripping-machine-contracts/commit/6ee32b68d3c6bdd0cce5e9e6d76827d0909a1820))

## [0.6.0](https://github.com/uprightbass360/automatic-ripping-machine-contracts/compare/v0.5.1...v0.6.0) (2026-05-02)


### Features

* **enums:** add TranscodePhase enum ([230a4a8](https://github.com/uprightbass360/automatic-ripping-machine-contracts/commit/230a4a8b6b9566d17a48b13a57a97188aac96bb9))
* ExpectedTitle pydantic contract + Job.expected_titles field ([1bc0e99](https://github.com/uprightbass360/automatic-ripping-machine-contracts/commit/1bc0e9922fb93874be19b632dd07687d17bbfb32))
* Track contract adds process and skip_reason fields ([497da3c](https://github.com/uprightbass360/automatic-ripping-machine-contracts/commit/497da3c5f9dfdb8e84b0cf3cc90a1bf1c46cc40e))


### Bug Fixes

* **progress:** rip_progress/music_progress are floats not ints ([67eba7b](https://github.com/uprightbass360/automatic-ripping-machine-contracts/commit/67eba7b74318faf9e430c9cc67522b2ba890d6b3))

## [0.5.1](https://github.com/uprightbass360/automatic-ripping-machine-contracts/compare/v0.5.0...v0.5.1) (2026-04-29)


### Bug Fixes

* **job:** allow JobSummary to validate ORM rows ([c326774](https://github.com/uprightbass360/automatic-ripping-machine-contracts/commit/c3267741bcd9e3cf47be8b85066adbd929d9d754))

## [0.5.0](https://github.com/uprightbass360/automatic-ripping-machine-contracts/compare/v0.4.0...v0.5.0) (2026-04-29)


### Features

* add Job, JobSummary, Track, TrackCounts, JobProgressState contracts ([ece12c0](https://github.com/uprightbass360/automatic-ripping-machine-contracts/commit/ece12c08f7ce77042d7693d8c89ab81c0650b6d6))

## [0.4.0](https://github.com/uprightbass360/automatic-ripping-machine-contracts/compare/v0.3.0...v0.4.0) (2026-04-26)


### Features

* **enums:** add JobStatus.transcoding wire-only callback member ([4dc451b](https://github.com/uprightbass360/automatic-ripping-machine-contracts/commit/4dc451b8bbd333ab33a24bd913e20fb047246df9))

## [0.3.0](https://github.com/uprightbass360/automatic-ripping-machine-contracts/compare/v0.2.1...v0.3.0) (2026-04-26)


### Features

* **webhook:** add WebhookPayload + TranscodeCallbackPayload contracts ([f47df4a](https://github.com/uprightbass360/automatic-ripping-machine-contracts/commit/f47df4a23f91f909f3ce66b9c4016ee3551cfcf4))

## [0.2.1](https://github.com/uprightbass360/automatic-ripping-machine-contracts/compare/v0.2.0...v0.2.1) (2026-04-23)


### Bug Fixes

* drop Python 3.11 requirement for arm-neu 3.10 base-image compat ([461f5c3](https://github.com/uprightbass360/automatic-ripping-machine-contracts/commit/461f5c36ae2828767eb10442cecb4afe4a91d162))

## [0.2.0](https://github.com/uprightbass360/automatic-ripping-machine-contracts/compare/v0.1.0...v0.2.0) (2026-04-22)


### Features

* add shared enums (JobStatus, Disctype, VideoType, TierName, SchemeSlug) ([c0a3a11](https://github.com/uprightbass360/automatic-ripping-machine-contracts/commit/c0a3a115ff0e9794fcb92ed9b9082db43130ce16))
* add SharedOverrides and TierOverrides models ([6442a98](https://github.com/uprightbass360/automatic-ripping-machine-contracts/commit/6442a987eb2d8361c569a31c97cda55fa3db87c8))
* add TierOverridesByName and TranscodeOverrides envelope ([7393402](https://github.com/uprightbass360/automatic-ripping-machine-contracts/commit/73934023d2571aa8d184f049d6235c7e2b654822))
* add TranscodeJobConfig wire envelope ([9c8fea2](https://github.com/uprightbass360/automatic-ripping-machine-contracts/commit/9c8fea2dfd8542f13fd566b1c8d5acaf0e538a48))


### Bug Fixes

* correct Disctype wire values and harden enum tests ([d41cadf](https://github.com/uprightbass360/automatic-ripping-machine-contracts/commit/d41cadf8999fca954d2714b59f48ed843789226d))

## Changelog
