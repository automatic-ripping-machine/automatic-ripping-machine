"""Tests that ExpectedTitle data flows through Job detail and list endpoints."""
import pytest

from arm.database import db


@pytest.fixture
def client(app_context):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from arm.api.v1.jobs import router

    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as c:
        yield c


def test_job_detail_includes_expected_titles(client, app_context, sample_job):
    from arm.models.expected_title import ExpectedTitle

    db.session.add(ExpectedTitle(
        job_id=sample_job.job_id,
        source="omdb",
        title="Inception",
        runtime_seconds=8523,
        external_id="tt1375666",
    ))
    db.session.commit()

    response = client.get(f"/api/v1/jobs/{sample_job.job_id}/detail")
    assert response.status_code == 200
    data = response.json()
    assert "job" in data
    assert "expected_titles" in data["job"]
    titles = data["job"]["expected_titles"]
    assert len(titles) == 1
    assert titles[0]["source"] == "omdb"
    assert titles[0]["title"] == "Inception"
    assert titles[0]["runtime_seconds"] == 8523
    assert titles[0]["external_id"] == "tt1375666"
    assert titles[0]["season"] is None
    assert titles[0]["episode_number"] is None


def test_job_detail_with_no_expected_titles_returns_empty_list(client, app_context, sample_job):
    response = client.get(f"/api/v1/jobs/{sample_job.job_id}/detail")
    assert response.status_code == 200
    data = response.json()
    assert data["job"]["expected_titles"] == []


def test_job_detail_includes_tv_episode_rows(client, app_context, sample_job):
    """TV jobs have multiple ExpectedTitle rows (one per episode)."""
    from arm.models.expected_title import ExpectedTitle

    for n in range(1, 4):
        db.session.add(ExpectedTitle(
            job_id=sample_job.job_id,
            source="tvdb",
            title=f"Episode {n}",
            season=1,
            episode_number=n,
            runtime_seconds=2820 + n,
        ))
    db.session.commit()

    response = client.get(f"/api/v1/jobs/{sample_job.job_id}/detail")
    assert response.status_code == 200
    titles = response.json()["job"]["expected_titles"]
    assert len(titles) == 3
    assert all(t["source"] == "tvdb" for t in titles)
    nums = sorted(t["episode_number"] for t in titles)
    assert nums == [1, 2, 3]
