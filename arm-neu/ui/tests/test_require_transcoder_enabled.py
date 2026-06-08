import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from backend.config import settings
from backend.dependencies import require_transcoder_enabled


@pytest.fixture
def app_with_gated_route():
    app = FastAPI()

    @app.get("/gated", dependencies=[pytest.importorskip("fastapi").Depends(require_transcoder_enabled)])
    async def gated():
        return {"ok": True}

    return app


def test_raises_503_when_disabled(monkeypatch):
    monkeypatch.setattr(settings, "transcoder_enabled", False)
    with pytest.raises(HTTPException) as exc:
        require_transcoder_enabled()
    assert exc.value.status_code == 503
    assert "Transcoder disabled" in exc.value.detail


def test_noop_when_enabled(monkeypatch):
    monkeypatch.setattr(settings, "transcoder_enabled", True)
    # Should not raise. require_transcoder_enabled returns None implicitly;
    # the contract is "does not raise", so we don't assert on the return.
    require_transcoder_enabled()
