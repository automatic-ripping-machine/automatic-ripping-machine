"""Demo mode: flag, transport wiring, production fallback, and seed data."""
from __future__ import annotations


def test_demo_mode_defaults_false():
    from backend.config import Settings
    assert Settings().demo_mode is False


def test_factories_make_job_dict_is_demo_builder():
    """tests/factories.py must re-export the demo builder (no drift)."""
    import tests.factories as factories
    import backend.demo.data as demo_data
    assert factories.make_job_dict is demo_data.make_job_dict


def test_make_job_dict_has_core_fields():
    from backend.demo.data import make_job_dict
    job = make_job_dict(job_id=7, title="Demo")
    assert job["job_id"] == 7
    assert job["title"] == "Demo"
    assert job["track_counts"] == {"total": 5, "ripped": 0}


def test_entity_builders_exist():
    from backend.demo import data
    assert data.make_track_dict(track_id=1, job_id=1)["job_id"] == 1
    assert data.make_drive_dict(drive_id=2)["drive_id"] == 2
    assert data.make_notification_dict(id=3)["id"] == 3
    assert data.make_channel_dict(id=4, type="webhook")["type"] == "webhook"
    assert data.make_dispatch_dict(id=5, channel_id=4)["channel_id"] == 4
    assert data.make_transcode_job_dict(id=6)["status"] == "processing"
    assert data.make_preset_dict(slug="h264-fast")["slug"] == "h264-fast"


def test_build_demo_store_covers_states():
    from backend.demo.data import build_demo_store
    store = build_demo_store()
    statuses = {j["status"] for j in store.jobs}
    assert {"active", "waiting", "success", "fail"} <= statuses
    disctypes = {j["disctype"] for j in store.jobs}
    assert {"dvd", "bluray", "music"} <= disctypes
    assert any(j["status"] == "active" for j in store.jobs)
    assert len(store.drives) >= 2
    assert any(n["seen"] is False for n in store.notifications)
    assert {c["type"] for c in store.channels} == {"apprise", "webhook", "bash"}
    assert any(t["status"] == "processing" for t in store.transcode_jobs)
    assert store.setup_status["first_run"] is False


def test_store_job_lookup_and_tracks():
    from backend.demo.data import build_demo_store
    store = build_demo_store()
    jid = store.jobs[0]["job_id"]
    assert store.job(jid)["job_id"] == jid
    assert isinstance(store.tracks_for(jid), list)


import pytest
import httpx as _httpx


def _match(routes, method, path):
    for m, pattern, fn in routes:
        if m == method:
            got = pattern.match(path)
            if got:
                return fn, got.groupdict()
    return None, None


def test_arm_routes_serve_jobs():
    from backend.demo.routes_arm import ROUTES
    from backend.demo.data import build_demo_store
    store = build_demo_store()
    fn, params = _match(ROUTES, "GET", "/api/v1/jobs/paginated")
    req = _httpx.Request("GET", "https://arm/api/v1/jobs/paginated")
    resp = fn(req, store, **params)
    assert resp.status_code == 200
    assert len(resp.json()["jobs"]) == len(store.jobs)


def test_arm_routes_job_detail_by_id():
    from backend.demo.routes_arm import ROUTES
    from backend.demo.data import build_demo_store
    store = build_demo_store()
    fn, params = _match(ROUTES, "GET", "/api/v1/jobs/1/detail")
    req = _httpx.Request("GET", "https://arm/api/v1/jobs/1/detail")
    resp = fn(req, store, **params)
    assert resp.json()["job"]["job_id"] == 1
    assert "tracks" in resp.json()


def test_transcoder_routes_serve_jobs_and_health():
    from backend.demo.routes_transcoder import ROUTES
    from backend.demo.data import build_demo_store
    store = build_demo_store()
    fn, params = _match(ROUTES, "GET", "/health")
    req = _httpx.Request("GET", "https://t/health")
    assert fn(req, store, **params).json()["status"] == "online"
    fn, params = _match(ROUTES, "GET", "/jobs")
    req = _httpx.Request("GET", "https://t/jobs?status=processing")
    body = fn(req, store, **params).json()
    assert all(j["status"] == "processing" for j in body["jobs"])


def test_transcoder_jobs_filter_by_job_id():
    from backend.demo.routes_transcoder import ROUTES
    from backend.demo.data import build_demo_store
    store = build_demo_store()
    fn, params = _match(ROUTES, "GET", "/jobs")
    req = _httpx.Request("GET", "https://t/jobs?job_id=2&limit=1")
    body = fn(req, store, **params).json()
    assert len(body["jobs"]) == 1
    assert body["jobs"][0]["id"] == 2


async def test_demo_transport_serves_mapped_route():
    from backend.demo.transport import make_demo_client
    client = make_demo_client("arm", base_url="https://arm-test:8080", timeout=10.0)
    try:
        resp = await client.get("/api/v1/jobs/active")
        assert resp.status_code == 200
        assert "jobs" in resp.json()
    finally:
        await client.aclose()


async def test_demo_transport_unmapped_falls_through_to_real():
    """Unmapped path must hit the real transport (production), not demo data."""
    from backend.demo.transport import make_demo_client
    client = make_demo_client("arm", base_url="https://127.0.0.1:1/nope", timeout=0.5)
    try:
        with pytest.raises(_httpx.HTTPError):
            await client.get("/api/v1/this/path/is/not/mapped")
    finally:
        await client.aclose()


def test_get_client_off_uses_real_transport(monkeypatch):
    from backend.config import settings
    from backend.services import arm_client
    monkeypatch.setattr(settings, "demo_mode", False)
    arm_client._client = None
    client = arm_client.get_client()
    from backend.demo.transport import DemoTransport
    assert not isinstance(client._transport, DemoTransport)


def test_get_client_on_uses_demo_transport(monkeypatch):
    from backend.config import settings
    from backend.services import arm_client, transcoder_client
    from backend.demo.transport import DemoTransport
    monkeypatch.setattr(settings, "demo_mode", True)
    arm_client._client = None
    transcoder_client._client = None
    assert isinstance(arm_client.get_client()._transport, DemoTransport)
    assert isinstance(transcoder_client.get_client()._transport, DemoTransport)


def test_demo_transport_rejects_unknown_service():
    from backend.demo.transport import DemoTransport
    with pytest.raises(ValueError):
        DemoTransport("bogus", _httpx.AsyncHTTPTransport())


# ---------------------------------------------------------------------------
# End-to-end tests: real FastAPI app with demo mode ON
# ---------------------------------------------------------------------------

@pytest.fixture
def demo_on(monkeypatch):
    """Enable demo mode and reset client singletons so get_client() returns
    the demo transport for both ARM and transcoder."""
    from backend.config import settings
    from backend.services import arm_client, transcoder_client
    monkeypatch.setattr(settings, "demo_mode", True)
    arm_client._client = None
    transcoder_client._client = None
    yield


async def test_dashboard_populated_in_demo(demo_on, app_client):
    """GET /api/dashboard returns 200 with active jobs and a notification count."""
    resp = await app_client.get("/api/dashboard")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # active_jobs may be None when ARM is unreachable, but in demo mode it must
    # be a populated list (the demo store has at least one active job).
    assert body["active_jobs"] is not None
    assert len(body["active_jobs"]) >= 1
    # notification_count reflects unseen demo notifications.
    assert body["notification_count"] is not None
    assert body["notification_count"] >= 1
    # active_transcodes is always a list; demo has a processing transcode job.
    assert len(body["active_transcodes"]) >= 1


async def test_jobs_list_and_detail_in_demo(demo_on, app_client):
    """GET /api/jobs returns >= 4 jobs; GET /api/jobs/{id} returns 200."""
    listing = await app_client.get("/api/jobs")
    assert listing.status_code == 200, listing.text
    body = listing.json()
    # Response is JobListResponse: {jobs, total, page, per_page, pages}
    jobs = body["jobs"]
    assert len(jobs) >= 4, f"expected >= 4 jobs, got {len(jobs)}"
    # Pydantic serialised each job through JobSchema — spot-check required fields.
    first = jobs[0]
    assert "job_id" in first
    assert "status" in first
    assert "disctype" in first
    # Fetch the detail for the first job.
    detail_resp = await app_client.get(f"/api/jobs/{first['job_id']}")
    assert detail_resp.status_code == 200, detail_resp.text
    detail = detail_resp.json()
    assert detail["job_id"] == first["job_id"]
    # JobDetailSchema adds tracks and config on top of JobSchema.
    assert "tracks" in detail
    assert isinstance(detail["tracks"], list)


async def test_drives_and_notification_channels_in_demo(demo_on, app_client):
    """GET /api/drives returns >= 2 drives; GET /api/notifications/channels
    returns all three channel types (apprise, webhook, bash)."""
    drives_resp = await app_client.get("/api/drives")
    assert drives_resp.status_code == 200, drives_resp.text
    drives = drives_resp.json()
    # Response is list[DriveSchema].
    assert isinstance(drives, list)
    assert len(drives) >= 2
    assert all("drive_id" in d for d in drives)

    chans_resp = await app_client.get("/api/notifications/channels")
    assert chans_resp.status_code == 200, chans_resp.text
    chans = chans_resp.json()
    assert isinstance(chans, list)
    assert {c["type"] for c in chans} == {"apprise", "webhook", "bash"}


def test_demo_mutation_dismiss_all_marks_seen():
    from backend.demo.routes_arm import ROUTES
    from backend.demo.data import build_demo_store
    store = build_demo_store()
    assert any(not n["seen"] for n in store.notifications)
    fn, params = _match(ROUTES, "POST", "/api/v1/notifications/dismiss-all")
    req = _httpx.Request("POST", "https://arm/api/v1/notifications/dismiss-all")
    resp = fn(req, store, **params)
    assert resp.status_code == 200
    assert all(n["seen"] for n in store.notifications)


def test_demo_mutation_pause_and_start_job():
    from backend.demo.routes_arm import ROUTES
    from backend.demo.data import build_demo_store
    store = build_demo_store()
    fn, params = _match(ROUTES, "POST", "/api/v1/jobs/1/pause")
    req = _httpx.Request("POST", "https://arm/api/v1/jobs/1/pause")
    assert fn(req, store, **params).json()["success"] is True
    assert store.job(1)["status"] == "waiting"
    fn, params = _match(ROUTES, "POST", "/api/v1/jobs/1/start")
    req = _httpx.Request("POST", "https://arm/api/v1/jobs/1/start")
    assert fn(req, store, **params).json()["success"] is True
    assert store.job(1)["status"] == "active"


def test_demo_mutation_set_ripping_enabled_honors_body():
    from backend.demo.routes_arm import ROUTES
    from backend.demo.data import build_demo_store
    store = build_demo_store()
    fn, params = _match(ROUTES, "POST", "/api/v1/system/ripping-enabled")
    req = _httpx.Request("POST", "https://arm/api/v1/system/ripping-enabled",
                         json={"enabled": False})
    resp = fn(req, store, **params)
    assert resp.json()["enabled"] is False
    assert store.ripping_enabled["enabled"] is False


def test_demo_log_routes_structured_and_content():
    from backend.demo.routes_arm import ROUTES
    from backend.demo.data import build_demo_store
    store = build_demo_store()
    fn, params = _match(ROUTES, "GET", "/api/v1/logs/job_1.log/structured")
    req = _httpx.Request("GET", "https://arm/api/v1/logs/job_1.log/structured")
    body = fn(req, store, **params).json()
    assert body["filename"] == "job_1.log"
    assert len(body["entries"]) >= 1
    assert {"timestamp", "level", "event", "raw"} <= set(body["entries"][0])
    fn, params = _match(ROUTES, "GET", "/api/v1/logs/job_1.log")
    req = _httpx.Request("GET", "https://arm/api/v1/logs/job_1.log")
    c = fn(req, store, **params).json()
    assert c["filename"] == "job_1.log" and c["lines"] >= 1
    fn, params = _match(ROUTES, "GET", "/api/v1/logs")
    assert _match(ROUTES, "GET", "/api/v1/logs/job_1.log/structured")[0] is not None


async def test_demo_structured_log_through_app(demo_on, app_client):
    resp = await app_client.get("/api/logs/job_1.log/structured")
    assert resp.status_code == 200
    body = resp.json()
    assert body["filename"] == "job_1.log"
    assert len(body["entries"]) >= 1


# ---------------------------------------------------------------------------
# Regression guard: every page-level endpoint must return 200 in demo mode
# ---------------------------------------------------------------------------

DEMO_ENDPOINTS = [
    "/api/dashboard",
    "/api/metadata/search?q=Blade%20Runner",
    "/api/metadata/tt1856101",
    "/api/jobs/4/metadata",
    "/api/metadata/music/search?q=Abbey%20Road",
    "/api/metadata/music/abbey-road-1",
    "/api/jobs",
    "/api/jobs/1",
    "/api/jobs/3",
    "/api/jobs/3/naming-preview",
    "/api/drives",
    "/api/notifications",
    "/api/notifications/channels",
    "/api/config",
    "/api/settings",
    "/api/settings/transcoder/scheme",
    "/api/settings/transcoder/presets",
    "/api/logs",
    "/api/logs/job_1.log/structured",
    "/api/transcoder/jobs",
    "/api/transcoder/stats",
    "/api/transcoder/workers",
    "/api/transcoder/logs",
    "/api/transcoder/logs/transcode_1.log/structured",
    "/api/files/roots",
    "/api/files/list?path=/mnt/raw",
]


@pytest.mark.parametrize("path", DEMO_ENDPOINTS)
async def test_demo_endpoint_returns_200(demo_on, app_client, path):
    resp = await app_client.get(path)
    assert resp.status_code == 200, f"{path} -> {resp.status_code}: {resp.text[:300]}"
    # The SPA catch-all also returns 200 but with text/html; a real API
    # response must be JSON. This catches endpoints that fall through to the
    # SPA (e.g. a route whose path param can't match the requested value).
    assert resp.headers["content-type"].startswith("application/json"), (
        f"{path} returned {resp.headers['content-type']} (SPA fallthrough?)"
    )


async def test_demo_file_browser(demo_on, app_client):
    roots = await app_client.get("/api/files/roots")
    assert roots.status_code == 200
    assert any(r["path"] == "/mnt/raw" for r in roots.json())
    listing = await app_client.get("/api/files/list?path=/mnt/raw")
    assert listing.status_code == 200
    body = listing.json()
    assert body["path"] == "/mnt/raw"
    assert len(body["entries"]) >= 1
    assert any(e["type"] == "directory" for e in body["entries"])


def test_demo_transcode_logfiles_are_slash_free():
    """Transcode-job logfiles must be bare basenames. The UI's
    /transcoder/logs/{filename}/structured route is a single path segment;
    an absolute path (with slashes) gets percent-encoded and never matches,
    so the frontend's log fetch falls through to the SPA and breaks the card."""
    from backend.demo.data import build_demo_store
    store = build_demo_store()
    for job in store.transcode_jobs:
        assert "/" not in job["logfile"], job["logfile"]


def test_demo_poster_hosts_are_proxy_allowed():
    from urllib.parse import urlparse
    from backend.routers.images import _ALLOWED_IMAGE_HOSTS
    from backend.demo.data import build_demo_store
    store = build_demo_store()
    items = list(store.jobs) + list(store.transcode_jobs)
    posters = [i["poster_url"] for i in items if i.get("poster_url")]
    assert posters, "expected at least one real poster"
    for url in posters:
        assert url.startswith("https://"), url
        assert urlparse(url).hostname in _ALLOWED_IMAGE_HOSTS, url


async def test_demo_job_poster_survives_schema(demo_on, app_client):
    resp = await app_client.get("/api/jobs/1")
    assert resp.status_code == 200
    assert resp.json()["poster_url"] == (
        "https://image.tmdb.org/t/p/w500/gajva2L0rPYkEWjzgFlBXCAVBE5.jpg"
    )


async def test_demo_music_search_has_valid_covers(demo_on, app_client):
    from urllib.parse import urlparse
    from backend.routers.images import _ALLOWED_IMAGE_HOSTS
    resp = await app_client.get("/api/metadata/music/search?q=Abbey%20Road")
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert results
    for r in results:
        if r.get("poster_url"):
            assert "front-500" in r["poster_url"]  # not the 404-prone front-250
            assert urlparse(r["poster_url"]).hostname in _ALLOWED_IMAGE_HOSTS


def test_metadata_routes_dispatch_unambiguously():
    from backend.demo.routes_arm import ROUTES

    def match(path):
        for m, pat, fn in ROUTES:
            if m == "GET" and pat.match(path):
                return fn.__name__
        return None

    assert match("/api/v1/metadata/search") == "_metadata_search"
    assert match("/api/v1/metadata/music/search") == "_music_search"
    assert match("/api/v1/metadata/tt123") == "_metadata_detail"
    assert match("/api/v1/metadata/music/rel-1") == "_music_detail"
