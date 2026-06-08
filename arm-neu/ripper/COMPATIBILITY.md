# Service compatibility

This file declares the known-good service combinations arm-neu
targets at release time. It is NOT enforced by CI. Runtime
compatibility is governed by the `X-Api-Version` handshake
between arm-neu and the transcoder (see the transcoder's
`src/version.py` for the current `ACCEPTED_VERSIONS` set).

## Current (arm-neu 16.x)

- transcoder: `>=17.1, <18` (v17.1.0 introduced the preset system;
  v17.1.1 pinned HANDBRAKE_TAG + the snapshot-preset perf fix)
- ui: `>=16.0, <17`
- contracts: `>=0.2` (pinned precisely by `components/contracts` submodule SHA)

## Upgrade ordering

When a breaking change to the wire contract lands, upgrade in
this order to avoid webhook rejections:

1. Deploy the new transcoder.
2. Deploy the new arm-neu.
3. Deploy the new ui.

Rollback goes in reverse order. If a rollback crosses an X-Api-Version
bump, the older arm-neu's webhooks will be rejected by the newer
transcoder's receiver (by design - see transcoder PR #92). Either
roll all three services together or accept a brief gap in transcode
dispatch.
