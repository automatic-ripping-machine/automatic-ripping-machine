"""
Software (CPU) scheme.

Supports x265 and x264 software encoders with two built-in presets:
  software_balanced - good quality/speed balance (CRF 22 all tiers)
  software_quality  - high quality, slower (CRF 18/18/20)
"""

from presets import Encoder, Preset, Scheme

_AUDIO_ENCODERS = ["copy", "aac", "ac3", "eac3", "flac", "mp3"]
_SUBTITLE_MODES = ["all", "first", "none"]

_X265_SPEED_VALUES = [
    "ultrafast", "superfast", "veryfast", "faster", "fast",
    "medium", "slow", "slower", "veryslow", "placebo",
]

SCHEME = Scheme(
    slug="software",
    name="Software (CPU)",
    supported_encoders=[
        Encoder(
            slug="x265",
            name="Software x265",
            tuning_presets=_X265_SPEED_VALUES,
        ),
        Encoder(
            slug="x264",
            name="Software x264",
            tuning_presets=_X265_SPEED_VALUES,
        ),
    ],
    supported_audio_encoders=_AUDIO_ENCODERS,
    supported_subtitle_modes=_SUBTITLE_MODES,
    advanced_fields={
        "x265_preset": {
            "type": "enum",
            "values": _X265_SPEED_VALUES,
            "default": "slow",
            "description": "x265 speed/quality tradeoff",
        },
    },
    built_in_presets=[
        Preset(
            slug="software_balanced",
            name="Balanced",
            scheme="software",
            description="Good balance of quality and speed (CPU x265)",
            shared={
                "video_encoder": "x265",
                "audio_encoder": "copy",
                "subtitle_mode": "all",
            },
            tiers={
                "dvd": {
                    "handbrake_preset": "H.265 MKV 720p30",
                    "video_quality": 22,
                    "handbrake_extra_args": ["--width", "1280"],
                },
                "bluray": {
                    "handbrake_preset": "H.265 MKV 1080p30",
                    "video_quality": 22,
                },
                "uhd": {
                    "handbrake_preset": "H.265 MKV 2160p60 4K",
                    "video_quality": 22,
                },
            },
        ),
        Preset(
            slug="software_quality",
            name="High Quality",
            scheme="software",
            description="High quality encode, slower (CPU x265)",
            shared={
                "video_encoder": "x265",
                "audio_encoder": "copy",
                "subtitle_mode": "all",
            },
            tiers={
                "dvd": {
                    "handbrake_preset": "H.265 MKV 720p30",
                    "video_quality": 18,
                    "handbrake_extra_args": ["--width", "1280"],
                },
                "bluray": {
                    "handbrake_preset": "H.265 MKV 1080p30",
                    "video_quality": 18,
                },
                "uhd": {
                    "handbrake_preset": "H.265 MKV 2160p60 4K",
                    "video_quality": 20,
                },
            },
        ),
    ],
)
