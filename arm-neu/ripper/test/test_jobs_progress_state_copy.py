import pytest


@pytest.fixture
def app_state(app_context):
    from arm.database import db
    from arm.models.app_state import AppState
    state = AppState(id=1, ripping_paused=False, setup_complete=True)
    db.session.add(state)
    db.session.commit()
    return state


@pytest.fixture
def client(app_context):
    from arm.app import app
    from fastapi.testclient import TestClient
    with TestClient(app, raise_server_exceptions=True) as client:
        yield client


def _make_job(status: str, disctype: str):
    """Create a Job in the test DB without exercising the udev hardware path."""
    from arm.database import db
    from arm.models.job import Job

    job = Job(devpath=None, _skip_hardware=True)
    job.title = "Test"
    job.status = status
    job.disctype = disctype
    job.logfile = "test.log"
    job.no_of_titles = 0
    db.session.add(job)
    db.session.commit()
    db.session.refresh(job)
    return job


def test_progress_state_includes_copy_fields_when_no_data(client, app_state, app_context):
    """No copy in flight - copy_progress and copy_stage are None."""
    from arm.models.job import JobState

    job = _make_job(JobState.VIDEO_RIPPING.value, "dvd")

    resp = client.get(f"/api/v1/jobs/{job.job_id}/progress-state")
    assert resp.status_code == 200
    data = resp.json()
    assert "copy_progress" in data
    assert "copy_stage" in data
    assert data["copy_progress"] is None
    assert data["copy_stage"] is None


def test_progress_state_returns_copy_progress_from_side_file(
    client, app_state, app_context, tmp_path, monkeypatch,
):
    """When the side-file exists, /progress-state surfaces its latest entry."""
    import arm.config.config as cfg
    from arm.models.job import JobState

    monkeypatch.setitem(cfg.arm_config, "LOGPATH", str(tmp_path))
    progress_dir = tmp_path / "progress"
    progress_dir.mkdir()

    job = _make_job(JobState.COPYING.value, "bluray")

    (progress_dir / f"{job.job_id}.copy.log").write_text(
        "scratch-to-media,73.5,1,/raw/abc/file.mkv\n"
    )

    resp = client.get(f"/api/v1/jobs/{job.job_id}/progress-state")
    assert resp.status_code == 200
    data = resp.json()
    assert data["copy_progress"] == pytest.approx(73.5)
    assert data["copy_stage"] == "scratch-to-media"
