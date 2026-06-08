"""Tests for shared enums."""
import pytest


def test_job_status_members():
    from arm_contracts import JobStatus
    assert JobStatus.pending == "pending"
    assert JobStatus.processing == "processing"
    assert JobStatus.completed == "completed"
    assert JobStatus.failed == "failed"
    assert JobStatus.partial == "partial"
    assert JobStatus.transcoding == "transcoding"
    assert JobStatus.cancelled == "cancelled"


def test_job_status_wire_only_members_validate_in_callback_payload():
    """partial + transcoding both validate in TranscodeCallbackPayload.

    Both are wire-only members (the transcoder never persists them) but
    they are sent to arm-neu's transcode-callback endpoint, so the typed
    payload must accept them.
    """
    from arm_contracts import JobStatus, TranscodeCallbackPayload
    for status in (JobStatus.partial, JobStatus.transcoding):
        p = TranscodeCallbackPayload(status=status)
        assert p.status == status


def test_job_status_is_str_enum():
    """JobStatus members must be usable as plain strings (StrEnum semantics)."""
    from arm_contracts import JobStatus
    assert isinstance(JobStatus.pending, str)
    assert JobStatus.pending == "pending"
    assert f"status={JobStatus.completed}" == "status=completed"


def test_disctype_members():
    from arm_contracts import Disctype
    assert set(Disctype) == {
        Disctype.dvd, Disctype.bluray, Disctype.bluray4k,
        Disctype.music, Disctype.data, Disctype.unknown,
    }
    assert Disctype.dvd == "dvd"
    assert Disctype.bluray4k == "bluray4k"
    assert Disctype.unknown == "unknown"


def test_video_type_members():
    from arm_contracts import VideoType
    assert set(VideoType) == {VideoType.movie, VideoType.series, VideoType.music, VideoType.unknown}
    assert VideoType.movie == "movie"
    assert VideoType.music == "music"


def test_tier_name_members():
    from arm_contracts import TierName
    assert set(TierName) == {TierName.dvd, TierName.bluray, TierName.uhd}
    # Value assertions: the preset system uses these exact strings as dict keys
    assert TierName.dvd == "dvd"
    assert TierName.bluray == "bluray"
    assert TierName.uhd == "uhd"


def test_scheme_slug_members():
    from arm_contracts import SchemeSlug
    assert set(SchemeSlug) == {
        SchemeSlug.software, SchemeSlug.nvidia, SchemeSlug.intel, SchemeSlug.amd,
    }
    # Value assertions: these drive GPU_VENDOR routing in the transcoder
    assert SchemeSlug.software == "software"
    assert SchemeSlug.nvidia == "nvidia"


def test_transcode_phase_members():
    from arm_contracts import TranscodePhase
    assert set(TranscodePhase) == {
        TranscodePhase.queued,
        TranscodePhase.copying_source,
        TranscodePhase.encoding,
        TranscodePhase.finalizing,
    }
    # Value assertions: the UI compares against these wire strings to pick
    # the right progress widget rendering
    assert TranscodePhase.queued == "queued"
    assert TranscodePhase.copying_source == "copying_source"
    assert TranscodePhase.encoding == "encoding"
    assert TranscodePhase.finalizing == "finalizing"


def test_transcode_phase_is_str_enum():
    """Phase members must be usable as plain strings (StrEnum semantics)."""
    from arm_contracts import TranscodePhase
    assert isinstance(TranscodePhase.encoding, str)
    assert f"phase={TranscodePhase.copying_source}" == "phase=copying_source"


def test_jobstate_string_serialization():
    from arm_contracts.enums import JobState
    assert str(JobState.SUCCESS) == "success"
    assert f"{JobState.TRANSCODE_WAITING}" == "waiting_transcode"


def test_jobstate_no_aliases():
    """v1.1.0 disambiguated the previous VIDEO/AUDIO_RIPPING and
    VIDEO_WAITING/MANUAL_WAIT_STARTED collisions."""
    from arm_contracts.enums import JobState
    assert JobState.AUDIO_RIPPING is not JobState.VIDEO_RIPPING
    assert JobState.AUDIO_RIPPING.value == "audio_ripping"
    assert JobState.VIDEO_RIPPING.value == "video_ripping"


def test_jobstate_pause_throttle_distinct():
    from arm_contracts.enums import JobState
    assert JobState.MANUAL_PAUSED.value == "manual_paused"
    assert JobState.MAKEMKV_THROTTLED.value == "makemkv_throttled"
    assert JobState.MANUAL_PAUSED is not JobState.MAKEMKV_THROTTLED


def test_jobstate_renamed_members_not_present():
    """Catch typos: the old member names must not exist post-rename."""
    from arm_contracts.enums import JobState
    assert not hasattr(JobState, "MANUAL_WAIT_STARTED")
    assert not hasattr(JobState, "VIDEO_WAITING")


def test_sourcetype_round_trip():
    from arm_contracts.enums import SourceType
    assert SourceType("disc") is SourceType.disc
    assert SourceType("folder") is SourceType.folder
    assert SourceType("iso") is SourceType.iso
    assert SourceType.iso.value == "iso"


def test_trackstatus_members():
    from arm_contracts.enums import TrackStatus
    expected = {"pending", "ripping", "encoding", "success",
                "transcoded", "transcode_failed", "failed"}
    assert {m.value for m in TrackStatus} == expected


def test_trackstatus_includes_failed():
    from arm_contracts.enums import TrackStatus
    expected = {"pending", "ripping", "encoding", "success",
                "transcoded", "transcode_failed", "failed"}
    assert {m.value for m in TrackStatus} == expected


def test_webhookeventtype_single_member():
    from arm_contracts.enums import WebhookEventType
    assert {m.value for m in WebhookEventType} == {"info"}


def test_skipreason_members():
    from arm_contracts.enums import SkipReason
    expected = {"too_short", "too_long", "makemkv_skipped",
                "user_disabled", "below_main_feature"}
    assert {m.value for m in SkipReason} == expected


def test_skipreason_reexported_from_track_module():
    """Backwards compat: arm_contracts.track.SkipReason still resolves."""
    from arm_contracts.track import SkipReason as TrackSkipReason
    from arm_contracts.enums import SkipReason as EnumsSkipReason
    assert TrackSkipReason is EnumsSkipReason


def test_track_skip_reason_field_accepts_valid_enum():
    from arm_contracts import Track
    from arm_contracts.enums import SkipReason
    t = Track(track_id=1, job_id=1, skip_reason=SkipReason.too_short)
    assert t.skip_reason is SkipReason.too_short


def test_track_skip_reason_field_rejects_invalid():
    import pytest
    from pydantic import ValidationError
    from arm_contracts import Track
    with pytest.raises(ValidationError):
        Track(track_id=1, job_id=1, skip_reason="not_a_real_reason")
