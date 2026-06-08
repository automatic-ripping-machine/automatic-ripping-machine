"""
AMD VAAPI/AMF scheme.

Supports VAAPI and AMF H.265/H.264 encoders with two built-in presets:
  amd_balanced - good quality/speed balance (CRF 22 all tiers)
  amd_quality  - high quality, slower (CRF 18/18/20)

AMD hardware encoders do not expose speed/tuning presets in HandBrake,
so advanced_fields is empty and tuning_presets lists are not set.
"""

from presets import Encoder, Preset, Scheme

_AUDIO_ENCODERS = ["copy", "aac", "ac3", "eac3", "flac", "mp3"]
_SUBTITLE_MODES = ["all", "first", "none"]

_HB_PRESET_1080P = "H.265 VCN 1080p"
_HB_PRESET_4K = "H.265 VCN 2160p 4K"

SCHEME = Scheme(
    slug="amd",
    name="AMD VAAPI/AMF",
    supported_encoders=[
        Encoder(slug="vaapi_h265", name="VAAPI H.265"),
        Encoder(slug="vaapi_h264", name="VAAPI H.264"),
        Encoder(slug="amf_h265", name="AMF H.265"),
        Encoder(slug="amf_h264", name="AMF H.264"),
    ],
    supported_audio_encoders=_AUDIO_ENCODERS,
    supported_subtitle_modes=_SUBTITLE_MODES,
    advanced_fields={},
    built_in_presets=[
        Preset(
            slug="amd_balanced",
            name="Balanced",
            scheme="amd",
            description="Good balance of quality and speed (AMD VAAPI H.265)",
            shared={
                "video_encoder": "vaapi_h265",
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
            slug="amd_quality",
            name="High Quality",
            scheme="amd",
            description="High quality encode, slower (AMD VAAPI H.265)",
            shared={
                "video_encoder": "vaapi_h265",
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
