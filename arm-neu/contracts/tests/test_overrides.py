"""Tests for overrides models."""
import pytest
from pydantic import ValidationError


# ── SharedOverrides ─────────────────────────────────────────────────────

def test_shared_overrides_all_defaults_none():
    from arm_contracts import SharedOverrides
    m = SharedOverrides()
    assert m.video_encoder is None
    assert m.audio_encoder is None
    assert m.subtitle_mode is None


def test_shared_overrides_known_fields():
    from arm_contracts import SharedOverrides
    m = SharedOverrides(
        video_encoder="x265",
        audio_encoder="aac",
        subtitle_mode="all",
    )
    assert m.video_encoder == "x265"
    assert m.audio_encoder == "aac"
    assert m.subtitle_mode == "all"


def test_shared_overrides_accepts_scheme_advanced_fields():
    """Scheme-specific advanced fields (x265_preset, nvenc_preset, etc.)
    pass through as extras because extra='allow'. They are validated by
    the transcoder's scheme-aware validator, not by this model."""
    from arm_contracts import SharedOverrides
    m = SharedOverrides.model_validate({
        "video_encoder": "x265",
        "x265_preset": "medium",
        "nvenc_preset": "p7",
    })
    assert m.video_encoder == "x265"
    # Extras survive round-trip
    dumped = m.model_dump()
    assert dumped["x265_preset"] == "medium"
    assert dumped["nvenc_preset"] == "p7"


# ── TierOverrides ───────────────────────────────────────────────────────

def test_tier_overrides_all_defaults_none():
    from arm_contracts import TierOverrides
    m = TierOverrides()
    assert m.handbrake_preset is None
    assert m.video_quality is None
    assert m.handbrake_extra_args is None


def test_tier_overrides_known_fields():
    from arm_contracts import TierOverrides
    m = TierOverrides(
        handbrake_preset="H.265 MKV 1080p30",
        video_quality=22,
        handbrake_extra_args=["--encoder-preset=medium"],
    )
    assert m.handbrake_preset == "H.265 MKV 1080p30"
    assert m.video_quality == 22
    assert m.handbrake_extra_args == ["--encoder-preset=medium"]


def test_tier_overrides_quality_range():
    """video_quality must be in CRF range [0, 51]."""
    from arm_contracts import TierOverrides
    with pytest.raises(ValidationError):
        TierOverrides(video_quality=-1)
    with pytest.raises(ValidationError):
        TierOverrides(video_quality=52)
    # Boundaries accepted
    assert TierOverrides(video_quality=0).video_quality == 0
    assert TierOverrides(video_quality=51).video_quality == 51


def test_tier_overrides_accepts_scheme_advanced_fields():
    from arm_contracts import TierOverrides
    m = TierOverrides.model_validate({
        "handbrake_preset": "H.265 MKV 720p30",
        "x265_preset": "slow",
    })
    assert m.handbrake_preset == "H.265 MKV 720p30"
    assert m.model_dump()["x265_preset"] == "slow"


def test_tier_overrides_accepts_empty_dict():
    """Partial-tier support: empty tier dict is valid."""
    from arm_contracts import TierOverrides
    m = TierOverrides.model_validate({})
    assert m.handbrake_preset is None


# ── TierOverridesByName ─────────────────────────────────────────────────

def test_tier_overrides_by_name_all_defaults():
    from arm_contracts import TierOverridesByName
    m = TierOverridesByName()
    assert m.dvd.handbrake_preset is None
    assert m.bluray.video_quality is None
    assert m.uhd.handbrake_extra_args is None


def test_tier_overrides_by_name_from_dict():
    from arm_contracts import TierOverridesByName
    m = TierOverridesByName.model_validate({
        "dvd": {"handbrake_preset": "H.265 MKV 720p30", "video_quality": 20},
        "bluray": {"handbrake_preset": "H.265 MKV 1080p30", "video_quality": 22},
        "uhd": {"handbrake_preset": "H.265 MKV 2160p60 4K", "video_quality": 24},
    })
    assert m.dvd.video_quality == 20
    assert m.bluray.video_quality == 22
    assert m.uhd.video_quality == 24


def test_tier_overrides_by_name_rejects_unknown_tier():
    """Unknown tier names must be rejected (closed set)."""
    from arm_contracts import TierOverridesByName
    with pytest.raises(ValidationError):
        TierOverridesByName.model_validate({
            "dvd": {},
            "bluray": {},
            "uhd": {},
            "epic_tier": {},  # not a real tier
        })


def test_tier_overrides_by_name_partial_tiers_ok():
    """Partial: only specifying some tiers is valid; others default."""
    from arm_contracts import TierOverridesByName
    m = TierOverridesByName.model_validate({"dvd": {"video_quality": 18}})
    assert m.dvd.video_quality == 18
    assert m.bluray.video_quality is None
    assert m.uhd.video_quality is None


# ── TranscodeOverrides ──────────────────────────────────────────────────

def test_transcode_overrides_all_defaults():
    from arm_contracts import TranscodeOverrides
    m = TranscodeOverrides()
    assert m.shared.video_encoder is None
    assert m.tiers.dvd.video_quality is None


def test_transcode_overrides_from_dict():
    from arm_contracts import TranscodeOverrides
    m = TranscodeOverrides.model_validate({
        "shared": {"audio_encoder": "aac", "subtitle_mode": "all"},
        "tiers": {
            "dvd": {"video_quality": 20},
            "bluray": {"video_quality": 22},
            "uhd": {"video_quality": 24},
        },
    })
    assert m.shared.audio_encoder == "aac"
    assert m.tiers.uhd.video_quality == 24


def test_transcode_overrides_rejects_unknown_top_level():
    """TranscodeOverrides has a closed top-level set: shared + tiers only."""
    from arm_contracts import TranscodeOverrides
    with pytest.raises(ValidationError):
        TranscodeOverrides.model_validate({
            "shared": {},
            "tiers": {},
            "bogus": 1,
        })


def test_transcode_overrides_round_trip_json():
    """Parse -> dump -> parse yields equal model."""
    import json
    from arm_contracts import TranscodeOverrides
    src = {
        "shared": {
            "video_encoder": "x265",
            "audio_encoder": "copy",
            "subtitle_mode": "all",
            "x265_preset": "medium",
        },
        "tiers": {
            "dvd": {"handbrake_preset": "H.265 MKV 720p30", "video_quality": 20},
            "bluray": {"handbrake_preset": "H.265 MKV 1080p30", "video_quality": 22},
            "uhd": {"handbrake_preset": "H.265 MKV 2160p60 4K", "video_quality": 24},
        },
    }
    m = TranscodeOverrides.model_validate(src)
    dumped = json.loads(m.model_dump_json())
    reparsed = TranscodeOverrides.model_validate(dumped)
    assert reparsed == m
