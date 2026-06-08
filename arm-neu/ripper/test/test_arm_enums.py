"""Tests for ripper-internal enums (arm/enums.py)."""


def test_ripmethod_members():
    from arm.enums import RipMethod
    assert {m.value for m in RipMethod} == {"mkv", "backup", "backup_dvd"}


def test_ripmethod_str_serialization():
    from arm.enums import RipMethod
    assert str(RipMethod.backup_dvd) == "backup_dvd"
    assert f"{RipMethod.mkv}" == "mkv"


def test_audio_title_source_members():
    from arm.enums import AudioTitleSource
    assert {m.value for m in AudioTitleSource} == {
        "none", "musicbrainz", "freecddb",
    }


def test_audio_format_members():
    from arm.enums import AudioFormat
    assert {m.value for m in AudioFormat} == {
        "flac", "mp3", "vorbis", "opus", "m4a", "wav", "mka",
        "wv", "ape", "mpc", "spx", "mp2", "tta", "aiff",
    }


def test_speed_profile_members():
    from arm.enums import SpeedProfile
    assert {m.value for m in SpeedProfile} == {"safe", "fast", "fastest"}


def test_speed_profile_drives_cdparanoia_dict():
    """The _SPEED_PROFILES dict in arm/ripper/utils.py keys MUST match
    SpeedProfile members. A rename to either side without the other
    would mean a config value passes API validation but yields no
    cdparanoia flags (silently falls back to default behavior)."""
    from arm.enums import SpeedProfile
    from arm.ripper.utils import _SPEED_PROFILES
    assert set(_SPEED_PROFILES.keys()) == {m.value for m in SpeedProfile}
