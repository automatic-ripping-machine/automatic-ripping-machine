"""
Intel QSV scheme.

Supports QSV H.265 and H.264 encoders with two built-in presets:
  intel_balanced - good quality/speed balance (CRF 22 all tiers)
  intel_quality  - high quality, slower (CRF 18/18/20)
"""

from presets import Encoder, Preset, Scheme

_AUDIO_ENCODERS = ["copy", "aac", "ac3", "eac3", "flac", "mp3"]
_SUBTITLE_MODES = ["all", "first", "none"]

_QSV_SPEED_VALUES = ["veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"]

_HB_PRESET_1080P = "H.265 QSV 1080p"
_HB_PRESET_4K = "H.265 QSV 2160p 4K"

SCHEME = Scheme(
    slug="intel",
    name="Intel QSV",
    supported_encoders=[
        Encoder(
            slug="qsv_h265",
            name="QSV H.265",
            tuning_presets=_QSV_SPEED_VALUES,
        ),
        Encoder(
            slug="qsv_h264",
            name="QSV H.264",
            tuning_presets=_QSV_SPEED_VALUES,
        ),
    ],
    supported_audio_encoders=_AUDIO_ENCODERS,
    supported_subtitle_modes=_SUBTITLE_MODES,
    advanced_fields={
        "qsv_preset": {
            "type": "enum",
            "values": _QSV_SPEED_VALUES,
            "default": "slow",
            "description": "QSV speed/quality tradeoff",
        },
    },
    built_in_presets=[
        Preset(
            slug="intel_balanced",
            name="Balanced",
            scheme="intel",
            description="Good balance of quality and speed (Intel QSV H.265)",
            shared={
                "video_encoder": "qsv_h265",
                "audio_encoder": "copy",
                "subtitle_mode": "all",
            },
            tiers={
                "dvd": {
                    "handbrake_preset": _HB_PRESET_1080P,
                    "video_quality": 22,
                    "handbrake_extra_args": ["--width", "1280"],
                },
                "bluray": {
                    "handbrake_preset": _HB_PRESET_1080P,
                    "video_quality": 22,
                },
                "uhd": {
                    "handbrake_preset": _HB_PRESET_4K,
                    "video_quality": 22,
                },
            },
        ),
        Preset(
            slug="intel_quality",
            name="High Quality",
            scheme="intel",
            description="High quality encode, slower (Intel QSV H.265)",
            shared={
                "video_encoder": "qsv_h265",
                "audio_encoder": "copy",
                "subtitle_mode": "all",
            },
            tiers={
                "dvd": {
                    "handbrake_preset": _HB_PRESET_1080P,
                    "video_quality": 18,
                    "handbrake_extra_args": ["--width", "1280"],
                },
                "bluray": {
                    "handbrake_preset": _HB_PRESET_1080P,
                    "video_quality": 18,
                },
                "uhd": {
                    "handbrake_preset": _HB_PRESET_4K,
                    "video_quality": 20,
                },
            },
        ),
    ],
)
