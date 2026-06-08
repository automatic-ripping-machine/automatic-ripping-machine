"""Ripper-internal enums.

Values that never cross a service boundary live here. Anything that
appears in a webhook payload, callback payload, or HTTP API response
that arm-ui consumes belongs in arm_contracts.enums instead.
"""
from enum import Enum


class _StrValueEnum(str, Enum):
    """Base for string-valued enums; mirrors arm_contracts._StrValueEnum
    so we don't drag the contracts package in for ripper-only types."""

    def __str__(self) -> str:
        return self.value

    def __format__(self, format_spec: str) -> str:
        return self.value.__format__(format_spec)


class RipMethod(_StrValueEnum):
    """MakeMKV rip strategy. Used for Job.config.RIPMETHOD.

    backup / backup_dvd are Blu-ray strategies (backup decrypts then
    copies; backup_dvd extracts via MakeMKV before post-processing).
    mkv is the default direct-to-MKV path used for DVDs and most
    Blu-rays.
    """
    mkv = "mkv"
    backup = "backup"
    backup_dvd = "backup_dvd"


class AudioTitleSource(_StrValueEnum):
    """Audio CD title lookup source. Used for Job.config.GET_AUDIO_TITLE."""
    none = "none"
    musicbrainz = "musicbrainz"
    freecddb = "freecddb"


class AudioFormat(_StrValueEnum):
    """abcde audio output format. Used for Job.config.AUDIO_FORMAT.

    Closed set; matches the formats abcde itself supports. Validated at the
    API boundary (arm/api/v1/jobs.py PUT /jobs/{id}/config) so a typo in a
    PATCH body fails fast rather than landing in the DB and surfacing later
    when abcde rejects the format.
    """
    flac = "flac"
    mp3 = "mp3"
    vorbis = "vorbis"
    opus = "opus"
    m4a = "m4a"
    wav = "wav"
    mka = "mka"
    wv = "wv"
    ape = "ape"
    mpc = "mpc"
    spx = "spx"
    mp2 = "mp2"
    tta = "tta"
    aiff = "aiff"


class SpeedProfile(_StrValueEnum):
    """cdparanoia error-correction profile. Used for Job.config.RIP_SPEED_PROFILE.

    Maps to cdparanoia flags via _SPEED_PROFILES in arm/ripper/utils.py:
      safe    -> "" (full paranoia, slowest, best for scratched discs)
      fast    -> "-Y" (disable extra paranoia, ~2-4x faster)
      fastest -> "-Z" (no error correction, pristine discs only, ~5-10x faster)
    """
    safe = "safe"
    fast = "fast"
    fastest = "fastest"
