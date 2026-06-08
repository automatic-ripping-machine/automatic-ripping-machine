"""API version constant for the cross-service ARM handshake.

Mirrors transcoder/src/version.py, but starts in LENIENT mode
(ACCEPT_MISSING_VERSION_HEADER = True) because not all transcoder
deployments stamp X-Api-Version on outbound callbacks yet (fixed
2026-04-29 in transcoder; needs deploy + soak before strict mode).

Bumped when the cross-service contract changes in a backwards-
incompatible way.

  v1 - pre-preset, flat encoding keys (video_encoder, handbrake_preset*, ...)
  v2 - preset-based shape (preset_slug + overrides dict)
"""

API_VERSION = "2"

# Versions accepted on inbound requests that opt into version checking
# (currently: the transcode-callback receiver).
ACCEPTED_VERSIONS = frozenset({"2"})

# When True, requests with no X-Api-Version header are accepted (lenient).
# When False, missing header returns 400.
#
# Lenient initially: until all deployed transcoders carry the post-2026-04-29
# fix, callbacks may arrive without the header. Flip to False once prod logs
# show all callbacks include the header. Tracked in memory:
# project_arm_neu_callback_strict_version_flip.md
ACCEPT_MISSING_VERSION_HEADER = True
