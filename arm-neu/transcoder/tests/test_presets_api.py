"""
Tests for preset CRUD API endpoints.
"""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker


# ---- Fixtures ---------------------------------------------------------------


@pytest_asyncio.fixture
async def client(mock_worker, tmp_path):
    """Async test client with real DB, active_scheme loaded, auth disabled."""
    db_path = str(tmp_path / "test.db")

    import database as db_module
    from models import Base

    test_engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
    test_session_factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False,
    )

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    @asynccontextmanager
    async def test_get_db():
        async with test_session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    with (
        patch.object(db_module, "get_db", test_get_db),
        patch("routers.presets.get_db", test_get_db),
        patch("routers.jobs.get_db", test_get_db),
        patch("routers.stats.get_db", test_get_db),
        patch("routers.config.get_db", test_get_db),
        patch("main.init_db", AsyncMock()),
    ):
        import main as main_module
        from presets import load_active_scheme

        main_module.active_scheme = load_active_scheme()
        main_module.app.state.worker = mock_worker

        transport = ASGITransport(app=main_module.app)
        # ASGITransport invokes the app in-process; base_url scheme is a placeholder
        # never resolved on the network. Using https to satisfy static analysis.
        async with AsyncClient(transport=transport, base_url="https://test") as ac:
            yield ac

        main_module.app.state.worker = None

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


# ---- GET /api/v1/scheme -----------------------------------------------------


class TestGetScheme:
    """Tests for GET /api/v1/scheme."""

    @pytest.mark.asyncio
    async def test_returns_software_scheme(self, client):
        resp = await client.get("/api/v1/scheme")
        assert resp.status_code == 200
        data = resp.json()
        assert data["slug"] == "software"
        assert data["name"] == "Software (CPU)"

    @pytest.mark.asyncio
    async def test_encoders_list(self, client):
        resp = await client.get("/api/v1/scheme")
        data = resp.json()
        encoder_slugs = [e["slug"] for e in data["supported_encoders"]]
        assert "x265" in encoder_slugs
        assert "x264" in encoder_slugs

    @pytest.mark.asyncio
    async def test_no_nvidia_encoders(self, client):
        resp = await client.get("/api/v1/scheme")
        data = resp.json()
        encoder_slugs = [e["slug"] for e in data["supported_encoders"]]
        assert "nvenc_h265" not in encoder_slugs

    @pytest.mark.asyncio
    async def test_audio_and_subtitle_fields(self, client):
        resp = await client.get("/api/v1/scheme")
        data = resp.json()
        assert "supported_audio_encoders" in data
        assert "copy" in data["supported_audio_encoders"]
        assert "supported_subtitle_modes" in data
        assert "all" in data["supported_subtitle_modes"]

    @pytest.mark.asyncio
    async def test_advanced_fields_present(self, client):
        resp = await client.get("/api/v1/scheme")
        data = resp.json()
        assert "advanced_fields" in data
        assert "x265_preset" in data["advanced_fields"]


# ---- GET /api/v1/presets ----------------------------------------------------


class TestGetPresets:
    """Tests for GET /api/v1/presets."""

    @pytest.mark.asyncio
    async def test_lists_built_in_presets(self, client):
        resp = await client.get("/api/v1/presets")
        assert resp.status_code == 200
        data = resp.json()
        presets = data["presets"]
        assert len(presets) >= 2
        slugs = [p["slug"] for p in presets]
        assert "software_balanced" in slugs
        assert "software_quality" in slugs

    @pytest.mark.asyncio
    async def test_built_in_presets_have_all_tiers(self, client):
        resp = await client.get("/api/v1/presets")
        for preset in resp.json()["presets"]:
            if preset["builtin"]:
                assert "dvd" in preset["tiers"]
                assert "bluray" in preset["tiers"]
                assert "uhd" in preset["tiers"]

    @pytest.mark.asyncio
    async def test_built_in_preset_shape(self, client):
        resp = await client.get("/api/v1/presets")
        preset = resp.json()["presets"][0]
        assert "slug" in preset
        assert "name" in preset
        assert "scheme" in preset
        assert "description" in preset
        assert "builtin" in preset
        assert preset["builtin"] is True


# ---- GET /api/v1/presets/{slug} ---------------------------------------------


class TestGetPresetBySlug:
    """Tests for GET /api/v1/presets/{slug}."""

    @pytest.mark.asyncio
    async def test_get_built_in_by_slug(self, client):
        resp = await client.get("/api/v1/presets/software_balanced")
        assert resp.status_code == 200
        data = resp.json()
        assert data["slug"] == "software_balanced"
        assert data["builtin"] is True

    @pytest.mark.asyncio
    async def test_404_for_nonexistent(self, client):
        resp = await client.get("/api/v1/presets/does-not-exist")
        assert resp.status_code == 404


# ---- POST /api/v1/presets ---------------------------------------------------


class TestCreateCustomPreset:
    """Tests for POST /api/v1/presets."""

    @pytest.mark.asyncio
    async def test_create_custom_preset(self, client):
        body = {
            "name": "My Custom",
            "parent_slug": "software_balanced",
            "overrides": {
                "shared": {"audio_encoder": "aac"},
                "tiers": {"dvd": {"video_quality": 20}},
            },
        }
        resp = await client.post("/api/v1/presets", json=body)
        assert resp.status_code == 201
        data = resp.json()
        assert data["slug"] == "my-custom"
        assert data["name"] == "My Custom"
        assert data["builtin"] is False
        assert data["parent_slug"] == "software_balanced"
        # Overrides should be merged into resolved tiers
        assert data["tiers"]["dvd"]["video_quality"] == 20
        # Shared override should be in the shared field
        assert data["shared"]["audio_encoder"] == "aac"

    @pytest.mark.asyncio
    async def test_invalid_parent_returns_400(self, client):
        body = {
            "name": "Bad Parent",
            "parent_slug": "nonexistent_parent",
        }
        resp = await client.post("/api/v1/presets", json=body)
        assert resp.status_code == 400
        assert "parent" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_missing_name_returns_400(self, client):
        body = {
            "parent_slug": "software_balanced",
        }
        resp = await client.post("/api/v1/presets", json=body)
        assert resp.status_code == 400
        assert "name" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_created_preset_appears_in_list(self, client):
        body = {
            "name": "Listed Preset",
            "parent_slug": "software_balanced",
            "overrides": {},
        }
        resp = await client.post("/api/v1/presets", json=body)
        assert resp.status_code == 201

        list_resp = await client.get("/api/v1/presets")
        slugs = [p["slug"] for p in list_resp.json()["presets"]]
        assert "listed-preset" in slugs

    @pytest.mark.asyncio
    async def test_duplicate_slug_returns_409(self, client):
        body = {
            "name": "Duplicate Test",
            "parent_slug": "software_balanced",
            "overrides": {},
        }
        resp1 = await client.post("/api/v1/presets", json=body)
        assert resp1.status_code == 201

        resp2 = await client.post("/api/v1/presets", json=body)
        assert resp2.status_code == 409

    @pytest.mark.asyncio
    async def test_invalid_encoder_override_returns_400(self, client):
        body = {
            "name": "Bad Encoder",
            "parent_slug": "software_balanced",
            "overrides": {
                "tiers": {"dvd": {"video_encoder": "nvenc_h265"}},
            },
        }
        resp = await client.post("/api/v1/presets", json=body)
        assert resp.status_code == 400
        assert "unsupported encoder" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_invalid_audio_override_returns_400(self, client):
        body = {
            "name": "Bad Audio",
            "parent_slug": "software_balanced",
            "overrides": {
                "shared": {"audio_encoder": "bogus_codec"},
            },
        }
        resp = await client.post("/api/v1/presets", json=body)
        assert resp.status_code == 400
        assert "unsupported audio" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_invalid_subtitle_override_returns_400(self, client):
        body = {
            "name": "Bad Subs",
            "parent_slug": "software_balanced",
            "overrides": {
                "shared": {"subtitle_mode": "burn_in"},
            },
        }
        resp = await client.post("/api/v1/presets", json=body)
        assert resp.status_code == 400
        assert "unsupported subtitle" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_invalid_tier_name_returns_400(self, client):
        body = {
            "name": "Bad Tier",
            "parent_slug": "software_balanced",
            "overrides": {
                "tiers": {"4k_super": {"video_quality": 18}},
            },
        }
        resp = await client.post("/api/v1/presets", json=body)
        assert resp.status_code == 400
        assert "unknown tier" in resp.json()["detail"].lower()


# ---- PATCH /api/v1/presets/{slug} -------------------------------------------


class TestUpdateCustomPreset:
    """Tests for PATCH /api/v1/presets/{slug}."""

    @pytest.mark.asyncio
    async def test_update_custom_preset(self, client):
        # Create first
        create_body = {
            "name": "Updatable",
            "parent_slug": "software_balanced",
            "overrides": {},
        }
        create_resp = await client.post("/api/v1/presets", json=create_body)
        assert create_resp.status_code == 201
        slug = create_resp.json()["slug"]

        # Update
        update_body = {
            "name": "Updatable v2",
            "overrides": {
                "shared": {"audio_encoder": "aac"},
            },
        }
        resp = await client.patch(f"/api/v1/presets/{slug}", json=update_body)
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Updatable v2"
        assert data["shared"]["audio_encoder"] == "aac"

    @pytest.mark.asyncio
    async def test_cannot_update_built_in(self, client):
        resp = await client.patch(
            "/api/v1/presets/software_balanced",
            json={"name": "Hacked"},
        )
        assert resp.status_code == 404
        assert "built-in" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_update_nonexistent_returns_404(self, client):
        resp = await client.patch(
            "/api/v1/presets/no-such-preset",
            json={"name": "Nope"},
        )
        assert resp.status_code == 404


# ---- DELETE /api/v1/presets/{slug} ------------------------------------------


class TestDeleteCustomPreset:
    """Tests for DELETE /api/v1/presets/{slug}."""

    @pytest.mark.asyncio
    async def test_delete_custom_preset(self, client):
        # Create first
        create_body = {
            "name": "Deletable",
            "parent_slug": "software_balanced",
            "overrides": {},
        }
        create_resp = await client.post("/api/v1/presets", json=create_body)
        assert create_resp.status_code == 201
        slug = create_resp.json()["slug"]

        # Delete
        resp = await client.delete(f"/api/v1/presets/{slug}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["deleted"] == slug

        # Confirm gone
        get_resp = await client.get(f"/api/v1/presets/{slug}")
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_cannot_delete_built_in(self, client):
        resp = await client.delete("/api/v1/presets/software_balanced")
        assert resp.status_code == 404
        assert "built-in" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_404(self, client):
        resp = await client.delete("/api/v1/presets/no-such-preset")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_clears_selected_preset_slug_when_it_matches(self, client):
        """Deleting the currently-active custom preset must null selected_preset_slug
        in the same transaction so the next job falls through to the scheme default
        instead of silently referencing a dangling slug."""
        from config import settings
        # Create a custom preset
        create_body = {
            "name": "Active Temp",
            "parent_slug": "software_balanced",
            "overrides": {},
        }
        create_resp = await client.post("/api/v1/presets", json=create_body)
        assert create_resp.status_code == 201
        slug = create_resp.json()["slug"]

        # Make it the active selection
        patch_resp = await client.patch(
            "/config", json={"selected_preset_slug": slug}
        )
        assert patch_resp.status_code == 200
        assert settings.selected_preset_slug == slug

        # Delete the active preset
        resp = await client.delete(f"/api/v1/presets/{slug}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["deleted"] == slug
        assert data["selection_cleared"] is True
        # Selection is cleared, so the next resolve falls back to scheme default
        assert settings.selected_preset_slug == ""

    @pytest.mark.asyncio
    async def test_delete_does_not_touch_selection_when_different(self, client):
        """Deleting a preset that is NOT the active selection leaves it alone."""
        from config import settings
        # Create two presets
        create_a = await client.post("/api/v1/presets", json={
            "name": "Active A", "parent_slug": "software_balanced", "overrides": {},
        })
        assert create_a.status_code == 201
        slug_a = create_a.json()["slug"]

        create_b = await client.post("/api/v1/presets", json={
            "name": "Unrelated B", "parent_slug": "software_balanced", "overrides": {},
        })
        assert create_b.status_code == 201
        slug_b = create_b.json()["slug"]

        # Pick A as the active selection
        await client.patch("/config", json={"selected_preset_slug": slug_a})
        assert settings.selected_preset_slug == slug_a

        try:
            # Delete B; A's selection must remain untouched
            resp = await client.delete(f"/api/v1/presets/{slug_b}")
            assert resp.status_code == 200
            assert resp.json()["selection_cleared"] is False
            assert settings.selected_preset_slug == slug_a
        finally:
            # Clean up: delete A so the selection auto-clears (mirroring real use)
            await client.delete(f"/api/v1/presets/{slug_a}")
            assert settings.selected_preset_slug == ""


# ---- Direct-call coverage for delete_preset --------------------------------
#
# The ASGI-client tests above exercise DELETE /api/v1/presets/{slug} end to
# end, but pytest-cov does not track line execution inside the
# `async with get_db()` block when the route is invoked via ASGITransport.
# We also call `delete_preset` directly as a coroutine below so coverage
# sees the branch inside the async context. Behavioural assertions live in
# the ASGI tests above - these exist purely to land the patch on lines
# coverage would otherwise miss.


class TestDeletePresetDirectCoverage:
    """Call delete_preset() directly to cover lines inside async with."""

    @pytest_asyncio.fixture
    async def db_setup(self, tmp_path):
        """Set up an in-memory test DB with active_scheme loaded."""
        db_path = str(tmp_path / "direct.db")
        import database as db_module
        from models import Base, CustomPresetDB, ConfigOverrideDB

        test_engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
        test_session_factory = async_sessionmaker(
            test_engine, class_=AsyncSession, expire_on_commit=False,
        )
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        @asynccontextmanager
        async def test_get_db():
            async with test_session_factory() as session:
                yield session

        with (
            patch.object(db_module, "get_db", test_get_db),
            patch("routers.presets.get_db", test_get_db),
        ):
            import main as main_module
            from presets import load_active_scheme
            main_module.active_scheme = load_active_scheme()

            yield test_session_factory, CustomPresetDB, ConfigOverrideDB

        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await test_engine.dispose()

    @pytest.mark.asyncio
    async def test_direct_delete_clears_active_selection(self, db_setup):
        factory, CustomPresetDB, ConfigOverrideDB = db_setup
        from config import settings
        from routers.presets import delete_preset

        # Seed a custom preset + make it the active selection
        async with factory() as session:
            session.add(CustomPresetDB(
                slug="custom-pick", name="Custom Pick",
                scheme="software", parent_slug="software_balanced",
                overrides_json="{}",
            ))
            session.add(ConfigOverrideDB(key="selected_preset_slug", value="custom-pick"))
            await session.commit()

        prior = settings.selected_preset_slug
        settings.selected_preset_slug = "custom-pick"
        try:
            result = await delete_preset(slug="custom-pick", _role="admin")
        finally:
            settings.selected_preset_slug = prior

        assert result == {"success": True, "deleted": "custom-pick", "selection_cleared": True}

        async with factory() as session:
            assert await session.get(CustomPresetDB, "custom-pick") is None
            assert await session.get(ConfigOverrideDB, "selected_preset_slug") is None

    @pytest.mark.asyncio
    async def test_direct_delete_unrelated_leaves_selection(self, db_setup):
        factory, CustomPresetDB, ConfigOverrideDB = db_setup
        from config import settings
        from routers.presets import delete_preset

        async with factory() as session:
            session.add(CustomPresetDB(
                slug="keep-me", name="Keep", scheme="software",
                parent_slug="software_balanced", overrides_json="{}",
            ))
            session.add(CustomPresetDB(
                slug="delete-me", name="Delete", scheme="software",
                parent_slug="software_balanced", overrides_json="{}",
            ))
            session.add(ConfigOverrideDB(key="selected_preset_slug", value="keep-me"))
            await session.commit()

        prior = settings.selected_preset_slug
        settings.selected_preset_slug = "keep-me"
        try:
            result = await delete_preset(slug="delete-me", _role="admin")
            assert result["selection_cleared"] is False
            # Override row for the kept selection is still present
            async with factory() as session:
                override = await session.get(ConfigOverrideDB, "selected_preset_slug")
                assert override is not None
                assert override.value == "keep-me"
        finally:
            settings.selected_preset_slug = prior

    @pytest.mark.asyncio
    async def test_direct_delete_nonexistent_raises_404(self, db_setup):
        from fastapi import HTTPException
        from routers.presets import delete_preset

        with pytest.raises(HTTPException) as exc_info:
            await delete_preset(slug="never-existed", _role="admin")
        assert exc_info.value.status_code == 404


# ---- Cross-scheme unavailable -----------------------------------------------


class TestCrossSchemeUnavailable:
    """A custom preset stored for a different scheme should show unavailable."""

    @pytest.mark.asyncio
    async def test_mismatched_scheme_shows_unavailable(self, client, tmp_path):
        """Directly insert a row with a non-matching scheme and verify response."""
        import database as db_module
        from models import CustomPresetDB

        # Insert a custom preset that was created under a different scheme
        async with db_module.get_db() as db:
            row = CustomPresetDB(
                slug="nvidia-fast",
                name="NVIDIA Fast",
                scheme="nvidia",
                parent_slug="nvenc_balanced",
                overrides_json="{}",
            )
            db.add(row)
            await db.commit()

        # Fetch via list
        list_resp = await client.get("/api/v1/presets")
        presets = list_resp.json()["presets"]
        nvidia_preset = next(p for p in presets if p["slug"] == "nvidia-fast")
        assert nvidia_preset["unavailable"] is True
        assert nvidia_preset["reason"] == "scheme mismatch"

        # Fetch by slug
        get_resp = await client.get("/api/v1/presets/nvidia-fast")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["unavailable"] is True
        assert data["reason"] == "scheme mismatch"
