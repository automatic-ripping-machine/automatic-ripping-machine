"""API version constant for the cross-service ARM handshake.

Bumped when the webhook payload shape (or other cross-service contract)
changes in a backwards-incompatible way.

  v1 - pre-preset, flat encoding keys (video_encoder, handbrake_preset*, ...)
  v2 - preset-based shape (preset_slug + overrides dict)
"""

API_VERSION = "2"

# Versions that the current transcoder accepts. All deployed arm-neu
# instances are on v16.0.0+, which stamps every webhook POST with
# X-Api-Version: 2, so the missing-header back-compat window from
# release N/N+1 is closed. Missing header now 400s.
ACCEPTED_VERSIONS = frozenset({"2"})
ACCEPT_MISSING_VERSION_HEADER = False  # enforced as of release N+2 (2026-04-21)
