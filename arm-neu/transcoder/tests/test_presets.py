"""
Tests for presets module - Encoder, Preset, Scheme, resolve_preset, load_active_scheme.
"""

import json
import os
import pytest
import pytest_asyncio
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from models import Base, CustomPresetDB

from presets import Encoder, Preset, Scheme, resolve_preset, load_active_scheme


# ─── TestEncoder ────────────────────────────────────────────────────────────


class TestEncoder:
    """Tests for Encoder model."""

    def test_create_minimal(self):
        """Create an encoder with just slug and name."""
        enc = Encoder(slug="x265", name="Software x265")
        assert enc.slug == "x265"
        assert enc.name == "Software x265"
        assert enc.tuning_presets == []

    def test_create_with_tuning_presets(self):
        """Create an encoder with tuning_presets list."""
        enc = Encoder(slug="nvenc_h265", name="NVENC H.265", tuning_presets=["film", "animation"])
        assert enc.slug == "nvenc_h265"
        assert enc.tuning_presets == ["film", "animation"]

    def test_tuning_presets_default_empty(self):
        """tuning_presets defaults to empty list when omitted."""
        enc = Encoder(slug="x264", name="Software x264")
        assert enc.tuning_presets == []

    def test_slug_required(self):
        """slug is required."""
        with pytest.raises(ValidationError):
            Encoder(name="No Slug")

    def test_name_required(self):
        """name is required."""
        with pytest.raises(ValidationError):
            Encoder(slug="x265")


# ─── TestPreset ─────────────────────────────────────────────────────────────


class TestPreset:
    """Tests for Preset model."""

    def _make_preset(self, **overrides):
        """Helper to build a valid preset dict."""
        defaults = dict(
            slug="balanced",
            name="Balanced",
            scheme="software",
            description="Good balance of quality and speed",
            shared={"video_quality": 22, "audio_encoder": "copy"},
            tiers={
                "dvd": {"handbrake_preset": "H.265 MKV 720p30", "handbrake_extra_args": ["--crop", "auto"]},
                "bluray": {"handbrake_preset": "H.265 MKV 1080p30"},
                "uhd": {"handbrake_preset": "H.265 MKV 2160p60 4K"},
            },
        )
        defaults.update(overrides)
        return defaults

    def test_create_valid_preset(self):
        """Create a valid preset with all three tiers."""
        p = Preset(**self._make_preset())
        assert p.slug == "balanced"
        assert p.name == "Balanced"
        assert p.scheme == "software"
        assert p.description == "Good balance of quality and speed"
        assert p.shared["video_quality"] == 22
        assert "dvd" in p.tiers
        assert "bluray" in p.tiers
        assert "uhd" in p.tiers

    def test_missing_dvd_tier_raises(self):
        """Missing dvd tier raises ValueError."""
        data = self._make_preset()
        del data["tiers"]["dvd"]
        with pytest.raises((ValueError, ValidationError)):
            Preset(**data)

    def test_missing_bluray_tier_raises(self):
        """Missing bluray tier raises ValueError."""
        data = self._make_preset()
        del data["tiers"]["bluray"]
        with pytest.raises((ValueError, ValidationError)):
            Preset(**data)

    def test_missing_uhd_tier_raises(self):
        """Missing uhd tier raises ValueError."""
        data = self._make_preset()
        del data["tiers"]["uhd"]
        with pytest.raises((ValueError, ValidationError)):
            Preset(**data)

    def test_shared_defaults_to_empty_dict(self):
        """shared defaults to empty dict when omitted."""
        data = self._make_preset()
        del data["shared"]
        p = Preset(**data)
        assert p.shared == {}

    def test_description_defaults_to_empty(self):
        """description defaults to empty string when omitted."""
        data = self._make_preset()
        del data["description"]
        p = Preset(**data)
        assert p.description == ""

    def test_slug_required(self):
        """slug is required."""
        data = self._make_preset()
        del data["slug"]
        with pytest.raises(ValidationError):
            Preset(**data)

    def test_name_required(self):
        """name is required."""
        data = self._make_preset()
        del data["name"]
        with pytest.raises(ValidationError):
            Preset(**data)

    def test_scheme_required(self):
        """scheme is required."""
        data = self._make_preset()
        del data["scheme"]
        with pytest.raises(ValidationError):
            Preset(**data)


# ─── TestResolvePreset ──────────────────────────────────────────────────────


class TestResolvePreset:
    """Tests for resolve_preset() function."""

    def _make_preset(self):
        """Return a Preset used by resolve_preset tests."""
        return Preset(
            slug="balanced",
            name="Balanced",
            scheme="software",
            shared={"video_quality": 22, "audio_encoder": "copy", "subtitle_mode": "all"},
            tiers={
                "dvd": {
                    "handbrake_preset": "H.265 MKV 720p30",
                    "handbrake_extra_args": ["--crop", "auto"],
                },
                "bluray": {
                    "handbrake_preset": "H.265 MKV 1080p30",
                },
                "uhd": {
                    "handbrake_preset": "H.265 MKV 2160p60 4K",
                },
            },
        )

    def test_no_overrides_returns_shared_plus_tier(self):
        """No overrides: result is shared merged with tier fields."""
        preset = self._make_preset()
        result = resolve_preset(preset, "bluray", overrides=None)
        assert result["video_quality"] == 22
        assert result["audio_encoder"] == "copy"
        assert result["handbrake_preset"] == "H.265 MKV 1080p30"

    def test_dvd_tier_includes_extra_args(self):
        """dvd tier includes handbrake_extra_args from tier dict."""
        preset = self._make_preset()
        result = resolve_preset(preset, "dvd", overrides=None)
        assert result["handbrake_preset"] == "H.265 MKV 720p30"
        assert result["handbrake_extra_args"] == ["--crop", "auto"]

    def test_bluray_has_no_extra_args(self):
        """bluray tier does not include handbrake_extra_args (not set in tier)."""
        preset = self._make_preset()
        result = resolve_preset(preset, "bluray", overrides=None)
        assert "handbrake_extra_args" not in result

    def test_shared_override_overrides_shared_field(self):
        """Shared override updates a field from the preset's shared dict."""
        preset = self._make_preset()
        result = resolve_preset(preset, "bluray", overrides={"shared": {"video_quality": 18}})
        assert result["video_quality"] == 18
        # other shared fields still present
        assert result["audio_encoder"] == "copy"
        assert result["handbrake_preset"] == "H.265 MKV 1080p30"

    def test_tier_override_overrides_tier_field(self):
        """Tier-level override updates a field from the tier dict."""
        preset = self._make_preset()
        result = resolve_preset(preset, "uhd", overrides={"tiers": {"uhd": {"handbrake_preset": "Custom 4K"}}})
        assert result["handbrake_preset"] == "Custom 4K"
        # shared fields still present
        assert result["video_quality"] == 22

    def test_both_overrides_applied(self):
        """Both shared and tier overrides are applied together."""
        preset = self._make_preset()
        result = resolve_preset(
            preset,
            "dvd",
            overrides={
                "shared": {"audio_encoder": "aac"},
                "tiers": {"dvd": {"handbrake_extra_args": ["--no-crop"]}},
            },
        )
        assert result["audio_encoder"] == "aac"
        assert result["handbrake_extra_args"] == ["--no-crop"]
        assert result["handbrake_preset"] == "H.265 MKV 720p30"
        assert result["video_quality"] == 22

    def test_tier_override_only_affects_selected_tier(self):
        """Tier override for dvd does not affect bluray resolution."""
        preset = self._make_preset()
        result_bluray = resolve_preset(
            preset,
            "bluray",
            overrides={"tiers": {"dvd": {"handbrake_preset": "Custom DVD"}}},
        )
        # bluray should be unaffected
        assert result_bluray["handbrake_preset"] == "H.265 MKV 1080p30"

    def test_overrides_empty_dict_treated_as_no_overrides(self):
        """Empty overrides dict behaves same as None."""
        preset = self._make_preset()
        result_none = resolve_preset(preset, "bluray", overrides=None)
        result_empty = resolve_preset(preset, "bluray", overrides={})
        assert result_none == result_empty


# ─── TestScheme ─────────────────────────────────────────────────────────────


class TestScheme:
    """Tests for Scheme model."""

    def _make_encoders(self):
        return [
            Encoder(slug="x265", name="Software x265"),
            Encoder(slug="x264", name="Software x264"),
        ]

    def _make_presets(self):
        tiers = {
            "dvd": {"handbrake_preset": "DVD"},
            "bluray": {"handbrake_preset": "Bluray"},
            "uhd": {"handbrake_preset": "UHD"},
        }
        return [
            Preset(slug="balanced", name="Balanced", scheme="software", tiers=tiers),
            Preset(slug="quality", name="High Quality", scheme="software", tiers=tiers),
        ]

    def _make_scheme(self, **overrides):
        defaults = dict(
            slug="software",
            name="Software (CPU)",
            supported_encoders=self._make_encoders(),
            supported_audio_encoders=["copy", "aac"],
            supported_subtitle_modes=["all", "none", "first"],
            advanced_fields={},
            built_in_presets=self._make_presets(),
        )
        defaults.update(overrides)
        return Scheme(**defaults)

    def test_create_scheme(self):
        """Create a scheme with all required fields."""
        scheme = self._make_scheme()
        assert scheme.slug == "software"
        assert scheme.name == "Software (CPU)"
        assert len(scheme.supported_encoders) == 2
        assert len(scheme.built_in_presets) == 2

    def test_encoder_slugs_property(self):
        """encoder_slugs returns list of encoder slug strings."""
        scheme = self._make_scheme()
        assert scheme.encoder_slugs == ["x265", "x264"]

    def test_get_preset_by_slug(self):
        """get_preset returns matching preset."""
        scheme = self._make_scheme()
        preset = scheme.get_preset("balanced")
        assert preset is not None
        assert preset.slug == "balanced"
        assert preset.name == "Balanced"

    def test_get_preset_second_item(self):
        """get_preset returns the second preset when requested by slug."""
        scheme = self._make_scheme()
        preset = scheme.get_preset("quality")
        assert preset is not None
        assert preset.slug == "quality"

    def test_get_preset_returns_none_for_unknown(self):
        """get_preset returns None for an unknown slug."""
        scheme = self._make_scheme()
        assert scheme.get_preset("nonexistent") is None

    def test_default_preset_is_first(self):
        """default_preset is the first preset in built_in_presets."""
        scheme = self._make_scheme()
        assert scheme.default_preset.slug == "balanced"

    def test_slug_required(self):
        """slug is required."""
        _p = Preset(slug="p", name="P", scheme="s", shared={},
                     tiers={"dvd": {}, "bluray": {}, "uhd": {}})
        with pytest.raises(ValidationError):
            Scheme(
                name="Missing Slug",
                supported_encoders=[],
                supported_audio_encoders=[],
                supported_subtitle_modes=[],
                advanced_fields={},
                built_in_presets=[_p],
            )

    def test_advanced_fields_defaults_to_empty(self):
        """advanced_fields defaults to empty dict when omitted."""
        _p = Preset(slug="p", name="P", scheme="s", shared={},
                     tiers={"dvd": {}, "bluray": {}, "uhd": {}})
        scheme = Scheme(
            slug="software",
            name="Software",
            supported_encoders=[],
            supported_audio_encoders=[],
            supported_subtitle_modes=[],
            built_in_presets=[_p],
        )
        assert scheme.advanced_fields == {}

    def test_empty_presets_rejected(self):
        """Scheme with no built-in presets is rejected."""
        with pytest.raises(ValueError, match="at least one"):
            Scheme(
                slug="s", name="S",
                supported_encoders=[], supported_audio_encoders=[],
                supported_subtitle_modes=[], built_in_presets=[],
            )


# ─── TestLoadActiveScheme ────────────────────────────────────────────────────


class TestLoadActiveScheme:
    """Tests for load_active_scheme() function."""

    def test_load_software_default(self, monkeypatch):
        """Missing GPU_VENDOR loads the software scheme with x265/x264 encoders."""
        monkeypatch.delenv("GPU_VENDOR", raising=False)
        scheme = load_active_scheme()
        assert scheme.slug == "software"
        assert len(scheme.built_in_presets) >= 1
        for enc in scheme.supported_encoders:
            assert enc.slug in ("x265", "x264")

    def test_load_nvidia(self, monkeypatch):
        """GPU_VENDOR=nvidia loads nvidia scheme with NVENC encoders only."""
        monkeypatch.setenv("GPU_VENDOR", "nvidia")
        scheme = load_active_scheme()
        assert scheme.slug == "nvidia"
        assert "nvenc_h265" in scheme.encoder_slugs
        assert "x265" not in scheme.encoder_slugs

    def test_load_intel(self, monkeypatch):
        """GPU_VENDOR=intel loads intel scheme with QSV encoders."""
        monkeypatch.setenv("GPU_VENDOR", "intel")
        scheme = load_active_scheme()
        assert scheme.slug == "intel"
        assert "qsv_h265" in scheme.encoder_slugs

    def test_load_amd(self, monkeypatch):
        """GPU_VENDOR=amd loads amd scheme with VAAPI or AMF encoders."""
        monkeypatch.setenv("GPU_VENDOR", "amd")
        scheme = load_active_scheme()
        assert scheme.slug == "amd"
        assert any(s.startswith("vaapi_") or s.startswith("amf_") for s in scheme.encoder_slugs)

    def test_each_scheme_presets_have_all_tiers(self, monkeypatch):
        """Every preset in every scheme defines all three tiers."""
        for vendor in ["nvidia", "intel", "amd", ""]:
            if vendor:
                monkeypatch.setenv("GPU_VENDOR", vendor)
            else:
                monkeypatch.delenv("GPU_VENDOR", raising=False)
            scheme = load_active_scheme()
            for preset in scheme.built_in_presets:
                assert set(preset.tiers.keys()) == {"dvd", "bluray", "uhd"}, (
                    f"Preset {preset.slug!r} in scheme {scheme.slug!r} missing tiers"
                )

    def test_each_scheme_encoders_used_in_presets_are_supported(self, monkeypatch):
        """video_encoder referenced in each tier belongs to the scheme's supported encoders."""
        for vendor in ["nvidia", "intel", "amd", ""]:
            if vendor:
                monkeypatch.setenv("GPU_VENDOR", vendor)
            else:
                monkeypatch.delenv("GPU_VENDOR", raising=False)
            scheme = load_active_scheme()
            valid_slugs = set(scheme.encoder_slugs)
            for preset in scheme.built_in_presets:
                for tier_name, tier in preset.tiers.items():
                    enc = tier.get("video_encoder")
                    if enc:
                        assert enc in valid_slugs, (
                            f"Encoder {enc!r} in tier {tier_name!r} of preset "
                            f"{preset.slug!r} not in scheme {scheme.slug!r} supported encoders"
                        )


# ─── TestCustomPresetDB ──────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


class TestCustomPresetDB:
    @pytest.mark.asyncio
    async def test_create_and_read(self, db_session):
        preset = CustomPresetDB(
            slug="my_anime",
            name="My Anime Preset",
            scheme="nvidia",
            parent_slug="nvidia_balanced",
            overrides_json=json.dumps({
                "shared": {"subtitle_mode": "all"},
                "tiers": {"bluray": {"video_quality": 18}},
            }),
        )
        db_session.add(preset)
        await db_session.commit()

        loaded = await db_session.get(CustomPresetDB, "my_anime")
        assert loaded is not None
        assert loaded.name == "My Anime Preset"
        assert loaded.scheme == "nvidia"
        assert loaded.parent_slug == "nvidia_balanced"
        overrides = json.loads(loaded.overrides_json)
        assert overrides["tiers"]["bluray"]["video_quality"] == 18
        assert loaded.created_at is not None
        assert loaded.updated_at is not None

    @pytest.mark.asyncio
    async def test_update(self, db_session):
        preset = CustomPresetDB(
            slug="my_preset", name="V1", scheme="nvidia",
            parent_slug="nvidia_balanced", overrides_json="{}",
        )
        db_session.add(preset)
        await db_session.commit()

        preset.name = "V2"
        preset.overrides_json = json.dumps({"shared": {"audio_encoder": "aac"}})
        await db_session.commit()

        loaded = await db_session.get(CustomPresetDB, "my_preset")
        assert loaded.name == "V2"
        assert "aac" in loaded.overrides_json
