"""Shared enums for the ARM fork cross-service wire contract.

Enums inherit from ``_StrValueEnum`` (str + Enum with __str__ override)
rather than ``StrEnum`` for Python 3.10 compatibility (arm-neu's base
image still ships 3.10.12). The __str__ override matches StrEnum's
behavior: ``str(Member)`` and f-string interpolation produce the value,
not ``ClassName.member``.
"""
from enum import Enum


class _StrValueEnum(str, Enum):
    """Base for string-valued enums, behaves like Python 3.11's StrEnum."""

    def __str__(self) -> str:
        return self.value

    def __format__(self, format_spec: str) -> str:
        return self.value.__format__(format_spec)


class JobStatus(_StrValueEnum):
    """Unified transcode job status.

    Members that persist to transcoder TranscodeJobDB.status:
      pending, processing, completed, failed, cancelled.

    Callback-only members (sent to arm-neu's transcode-callback endpoint
    but NEVER persisted in the transcoder's own JobStatus column):
      partial - emitted when some tracks succeeded and others failed;
        the transcoder always stores COMPLETED for that outcome and lets
        arm-neu decide how to represent it.
      transcoding - informational fire-and-forget heartbeat sent when a
        job leaves the queue and starts processing. The transcoder stores
        PROCESSING for that state; arm-neu maps the wire string to its
        own JobState.TRANSCODE_ACTIVE so the dashboard reflects the
        active phase.
    """
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"
    partial = "partial"              # callback wire only
    transcoding = "transcoding"      # callback wire only (informational)
    cancelled = "cancelled"


class Disctype(_StrValueEnum):
    """Disc media type as emitted by arm-neu on the wire.

    Note: UHD Blu-ray is 'bluray4k' here (see arm-neu
    arm/models/job.py:286 where get_disc_type sets disctype='bluray4k'
    for INDX0300 headers). The string 'uhd' is the preset tier name
    (see TierName), NOT a disctype value. These are separate concepts
    that happen to collide in natural English.
    """
    dvd = "dvd"
    bluray = "bluray"
    bluray4k = "bluray4k"
    music = "music"
    data = "data"
    unknown = "unknown"


class VideoType(_StrValueEnum):
    """High-level content classification used for folder layout."""
    movie = "movie"
    series = "series"
    music = "music"
    unknown = "unknown"


class TierName(_StrValueEnum):
    """Closed set of resolution tiers known to the preset system."""
    dvd = "dvd"
    bluray = "bluray"
    uhd = "uhd"


class SchemeSlug(_StrValueEnum):
    """Transcoder encoder scheme. Selected at transcoder boot from GPU probe."""
    software = "software"
    nvidia = "nvidia"
    intel = "intel"
    amd = "amd"


class TranscodePhase(_StrValueEnum):
    """Sub-status describing what the transcoder is doing inside JobStatus.processing.

    JobStatus is a coarse lifecycle (pending/processing/completed/failed);
    phase is a fine-grained progress signal so the UI can show "Copying source
    files" or "Finalizing" instead of an empty 0% bar during periods where no
    encoder progress is being reported. Designed for extension - new members
    can be added (e.g. extracting_audio, verifying_output) without breaking
    older consumers; safe consumers treat unknown values as a generic active
    state.
    """
    queued = "queued"
    copying_source = "copying_source"
    encoding = "encoding"
    finalizing = "finalizing"


class JobState(_StrValueEnum):
    """Possible states for arm-neu Job.status (the ripper-side lifecycle).

    Distinct from JobStatus (transcoder-side).

    Each member maps to a distinct wire string. Earlier versions
    aliased VIDEO_RIPPING/AUDIO_RIPPING (both -> "ripping") and
    MANUAL_WAIT_STARTED/VIDEO_WAITING (both -> "waiting") - consumers
    had to infer audio-vs-video from Job.disctype, and could not
    distinguish user-pause from concurrency-throttle. Disambiguated
    in v2.0.0; the renames are breaking on the wire (clients on
    older versions will see new strings they don't recognize) but
    safe consumers should treat unknown values as a generic active
    state rather than crash.

    MANUAL_WAIT_STARTED -> MANUAL_PAUSED ("manual_paused"):
      User-pause / manual-identify wait. Disctype-agnostic.
    VIDEO_WAITING -> MAKEMKV_THROTTLED ("makemkv_throttled"):
      Concurrency throttle while too many makemkvcon processes are
      running. System-initiated, not user-initiated.
    """
    SUCCESS = "success"
    FAILURE = "fail"
    MANUAL_PAUSED = "manual_paused"     # was MANUAL_WAIT_STARTED="waiting"
    IDENTIFYING = "identifying"
    IDLE = "ready"
    VIDEO_RIPPING = "video_ripping"     # was "ripping" (aliased with AUDIO_RIPPING)
    MAKEMKV_THROTTLED = "makemkv_throttled"  # was VIDEO_WAITING="waiting"
    VIDEO_INFO = "info"
    AUDIO_RIPPING = "audio_ripping"     # was "ripping" (aliased with VIDEO_RIPPING)
    COPYING = "copying"
    EJECTING = "ejecting"
    TRANSCODE_ACTIVE = "transcoding"
    TRANSCODE_WAITING = "waiting_transcode"


class SourceType(_StrValueEnum):
    """Job input source classification."""
    disc = "disc"
    folder = "folder"
    iso = "iso"


class TrackStatus(_StrValueEnum):
    """Per-track lifecycle.

    Designed for extension - new members can be added (e.g. queued,
    verifying) without breaking older consumers; safe consumers treat
    unknown values as a generic active state.

    Note: ``success`` is the rip-phase terminal; ``transcoded`` is the
    transcode-phase terminal. The two are intentionally distinct so the
    UI can color-code which lifecycle phase finished.

    Note: ``failed`` is the generic phase-agnostic per-track failure
    (e.g. a music rip subprocess failed before the transcode stage was
    ever reached). ``transcode_failed`` is reserved for failures during
    the transcode phase specifically. Consumers that only need a binary
    success/failure signal can treat both as terminal failures.
    """
    pending = "pending"
    ripping = "ripping"
    encoding = "encoding"
    success = "success"
    transcoded = "transcoded"
    transcode_failed = "transcode_failed"
    failed = "failed"   # generic per-track failure (e.g. music rip subprocess failed)


class WebhookEventType(_StrValueEnum):
    """Webhook payload classification.

    Single member today; the enum exists to close the wire contract so
    future event types are an explicit, breaking-change addition rather
    than a silent string typo.
    """
    info = "info"


class SkipReason(_StrValueEnum):
    """Reason a Track was filtered out of the rip set.

    Promoted from the previous typing.Literal alias in arm_contracts.track
    so the value set is introspectable and matches the _StrValueEnum
    pattern used by every other classification field on the wire.
    """
    too_short = "too_short"
    too_long = "too_long"
    makemkv_skipped = "makemkv_skipped"
    user_disabled = "user_disabled"
    below_main_feature = "below_main_feature"
