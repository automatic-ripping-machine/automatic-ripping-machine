"""Tests for TranscodeJobConfig wire envelope."""
import json

import pytest
from pydantic import ValidationError


def test_minimal_valid_config():
    from arm_contracts import TranscodeJobConfig
    m = TranscodeJobConfig(preset_slug="software-balanced")
    assert m.preset_slug == "software-balanced"
    assert m.overrides.shared.video_encoder is None
    assert m.delete_source is None
    assert m.output_extension is None


def test_full_config_with_overrides():
    from arm_contracts import TranscodeJobConfig
    src = {
        "preset_slug": "software-quality",
        "overrides": {
            "shared": {"audio_encoder": "aac"},
            "tiers": {
                "dvd": {"video_quality": 18},
            },
        },
        "delete_source": True,
        "output_extension": "mp4",
    }
    m = TranscodeJobConfig.model_validate(src)
    assert m.preset_slug == "software-quality"
    assert m.overrides.shared.audio_encoder == "aac"
    assert m.overrides.tiers.dvd.video_quality == 18
    assert m.delete_source is True
    assert m.output_extension == "mp4"


def test_preset_slug_required():
    from arm_contracts import TranscodeJobConfig
    with pytest.raises(ValidationError):
        TranscodeJobConfig.model_validate({})


@pytest.mark.parametrize("bad_slug", [
    "",                         # empty
    "With-Uppercase",           # uppercase not allowed
    "slug with spaces",         # spaces not allowed
    "slug.with.dots",           # dots not allowed
    "slug/with/slashes",        # slashes not allowed
    "-leading-hyphen",          # must start with alnum
    "_leading-underscore",      # must start with alnum
    "a" * 65,                   # too long (max 64)
])
def test_preset_slug_regex_rejects_bad(bad_slug):
    from arm_contracts import TranscodeJobConfig
    with pytest.raises(ValidationError):
        TranscodeJobConfig(preset_slug=bad_slug)


@pytest.mark.parametrize("good_slug", [
    "a",                        # single alnum
    "software-balanced",        # canonical shape
    "software_balanced",        # underscores OK
    "my-custom-preset-42",      # mixed with digits
    "a" * 64,                   # max length
])
def test_preset_slug_regex_accepts_good(good_slug):
    from arm_contracts import TranscodeJobConfig
    m = TranscodeJobConfig(preset_slug=good_slug)
    assert m.preset_slug == good_slug


def test_rejects_unknown_top_level_fields():
    """TranscodeJobConfig has a closed top-level set."""
    from arm_contracts import TranscodeJobConfig
    with pytest.raises(ValidationError):
        TranscodeJobConfig.model_validate({
            "preset_slug": "software-balanced",
            "bogus_key": "nope",
        })


def test_round_trip_json():
    from arm_contracts import TranscodeJobConfig
    src = {
        "preset_slug": "software-balanced",
        "overrides": {
            "shared": {"audio_encoder": "aac", "x265_preset": "medium"},
            "tiers": {
                "dvd": {"video_quality": 20},
                "bluray": {"video_quality": 22},
                "uhd": {"video_quality": 24},
            },
        },
        "delete_source": False,
        "output_extension": "mkv",
    }
    m = TranscodeJobConfig.model_validate(src)
    dumped = json.loads(m.model_dump_json())
    reparsed = TranscodeJobConfig.model_validate(dumped)
    assert reparsed == m
