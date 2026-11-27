"""Job detail page must render for jobs without a video type (unidentified or music discs)."""

import datetime

import pytest


def make_job(db, **values):
    from arm.models.job import Job

    job = Job.__mapper__.class_manager.new_instance()
    job.status, job.devpath, job.crc_id = "success", "/dev/jobdetail-test", "crc-jobdetail"
    job.start_time, job.ejected = datetime.datetime.now(), True
    for name, value in values.items():
        setattr(job, name, value)
    db.session.add(job)
    db.session.commit()
    return job


@pytest.fixture
def client(monkeypatch):
    from arm.ui import app, db, utils as ui_utils
    import arm.ui.routes  # noqa: F401 -- register the blueprints as runui does

    # Job detail looks up metadata online; keep the test offline.
    monkeypatch.setattr(ui_utils, "metadata_selector", lambda *args, **kwargs: None)
    with app.app_context():
        db.create_all()
        app.config.update(TESTING=True, LOGIN_DISABLED=True)
        yield app.test_client(), db
        db.session.rollback()
        db.session.remove()


@pytest.mark.parametrize("values", [
    {"title": "Unidentified disc", "video_type": None, "disctype": "dvd"},
    {"title": "Some Album", "video_type": None, "disctype": "music", "year": "1999"},
    {"title": "Some Album", "video_type": "music", "disctype": "music", "year": "1999"},
], ids=["no-video-type", "music-no-video-type", "music"])
def test_jobdetail_renders_without_video_type(client, values):
    test_client, db = client
    job = make_job(db, **values)

    response = test_client.get(f"/jobdetail?job_id={job.job_id}")

    assert response.status_code == 200
    assert values["title"] in response.get_data(as_text=True)


def test_jobdetail_still_shows_capitalized_video_type(client):
    test_client, db = client
    job = make_job(db, title="A Movie", video_type="movie", disctype="bluray", year="2001")

    page = test_client.get(f"/jobdetail?job_id={job.job_id}").get_data(as_text=True)

    assert "A Movie - Movie (2001)" in page
