"""
NVIDIA NVENC scheme.

Supports NVENC H.265 and H.264 encoders with three built-in presets:
  nvidia_balanced - good quality/speed balance (CRF 22/20/22)
  nvidia_quality  - high quality, slower (CRF 18/18/20)
  nvidia_fast     - fast encode, smaller file (CRF 26/24/26)
"""

from presets import Encoder, Preset, Scheme

_AUDIO_ENCODERS = ["copy", "aac", "ac3", "eac3", "flac", "mp3"]
_SUBTITLE_MODES = ["all", "first", "none"]

_NVENC_SPEED_VALUES = ["p1", "p2", "p3", "p4", "p5", "p6", "p7"]

_HB_PRESET_1080P = "H.265 NVENC 1080p"
_HB_PRESET_4K = "H.265 NVENC 2160p 4K"

SCHEME = Scheme(
    slug="nvidia",
    name="NVIDIA NVENC",
    supported_encoders=[
        Encoder(
            slug="nvenc_h265",
            name="NVENC H.265",
            tuning_presets=_NVENC_SPEED_VALUES,
        ),
        Encoder(
            slug="nvenc_h264",
            name="NVENC H.264",
            tuning_presets=_NVENC_SPEED_VALUES,
        ),
    ],
    supported_audio_encoders=_AUDIO_ENCODERS,
    supported_subtitle_modes=_SUBTITLE_MODES,
    advanced_fields={
        "nvenc_preset": {
            "type": "enum",
            "values": _NVENC_SPEED_VALUES,
            "default": "p4",
            "description": "NVENC speed/quality tradeoff (p1=fastest, p7=slowest)",
        },
    },
    built_in_presets=[
        Preset(
            slug="nvidia_balanced",
            name="Balanced",
            scheme="nvidia",
            description="Good balance of quality and speed (NVENC H.265)",
            shared={
                "video_encoder": "nvenc_h265",
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
                    "video_quality": 20,
                },
                "uhd": {
                    "handbrake_preset": _HB_PRESET_4K,
                    "video_quality": 22,
                },
            },
        ),
        Preset(
            slug="nvidia_quality",
            name="High Quality",
            scheme="nvidia",
            description="High quality encode, slower (NVENC H.265)",
            shared={
                "video_encoder": "nvenc_h265",
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
        Preset(
            slug="nvidia_fast",
            name="Fast",
            scheme="nvidia",
            description="Fast encode with smaller files (NVENC H.265, lower quality)",
            shared={
                "video_encoder": "nvenc_h265",
                "audio_encoder": "copy",
                "subtitle_mode": "all",
            },
            tiers={
                "dvd": {
                    "handbrake_preset": _HB_PRESET_1080P,
                    "video_quality": 26,
                    "handbrake_extra_args": ["--width", "1280"],
                },
                "bluray": {
                    "handbrake_preset": _HB_PRESET_1080P,
                    "video_quality": 24,
                },
                "uhd": {
                    "handbrake_preset": _HB_PRESET_4K,
                    "video_quality": 26,
                },
            },
        ),
    ],
)
