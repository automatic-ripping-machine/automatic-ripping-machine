"""State-changing /json modes need the header the UI sends; per-job edits stay out of arm.yaml."""
import datetime

import pytest


@pytest.fixture
def ui(monkeypatch):
    from arm.ui import app, db, utils as ui_utils
    import arm.ui.routes  # noqa: F401 -- register the blueprints as runui does

    monkeypatch.setattr(ui_utils, "metadata_selector", lambda *args, **kwargs: None)
    with app.app_context():
        db.create_all()
        app.config.update(TESTING=True, LOGIN_DISABLED=True)
        yield app, db
        db.session.rollback()
        db.session.remove()


def make_job(db, **values):
    from arm.models.job import Job

    job = Job.__mapper__.class_manager.new_instance()
    job.status, job.devpath, job.crc_id = "success", "/dev/sr-test", "crc-test"
    job.disctype, job.title, job.video_type = "dvd", "Some Movie", "movie"
    job.start_time, job.ejected = datetime.datetime.now(), False
    for name, value in values.items():
        setattr(job, name, value)
    db.session.add(job)
    db.session.commit()
    return job


XHR = {"X-Requested-With": "XMLHttpRequest"}


def test_json_delete_needs_the_ui_request_header(ui):
    from arm.models.job import Job

    app, db = ui
    job_id = make_job(db).job_id
    client = app.test_client()
    # e.g. <a href="http://arm:8080/json?mode=delete&job=..."> on another site
    response = client.get("/json", query_string={"mode": "delete", "job": job_id})
    assert response.status_code == 403
    assert db.session.get(Job, job_id) is not None
    data = client.get("/json", query_string={"mode": "delete", "job": job_id}, headers=XHR).get_json()
    assert data["success"] is True
    db.session.expire_all()
    assert db.session.get(Job, job_id) is None


def test_json_restart_needs_the_ui_request_header(ui, monkeypatch):
    from arm.ui import json_api

    app, db = ui
    # restart runs "pkill python3", which also stops any running rip
    monkeypatch.setattr(json_api, "restart_ui", lambda: pytest.fail("restarted from a plain GET"))
    response = app.test_client().get("/json", query_string={"mode": "restart"})
    assert response.status_code == 403


def test_read_only_json_modes_still_work_without_the_header(ui):
    app, db = ui
    response = app.test_client().get("/json", query_string={"mode": "joblist"})
    assert response.status_code == 200


def test_job_params_change_leaves_the_global_settings_alone(ui):
    import arm.config.config as cfg
    from arm.models.config import Config

    app, db = ui
    job = make_job(db)
    config = Config.__mapper__.class_manager.new_instance()
    config.job_id, config.MINLENGTH, config.MAXLENGTH, config.RIPMETHOD, config.MAINFEATURE = \
        job.job_id, "600", "99999", "mkv", False
    db.session.add(config)
    db.session.commit()
    before = {key: cfg.arm_config[key] for key in ("MINLENGTH", "MAXLENGTH", "RIPMETHOD", "MAINFEATURE")}
    data = app.test_client().get("/json", headers=XHR, query_string={
        "mode": "change_job_params", "config_id": job.job_id, "DISCTYPE": "dvd", "MINLENGTH": "1",
        "MAXLENGTH": "2", "RIPMETHOD": "backup", "MAINFEATURE": "true"}).get_json()
    assert data["success"] is True
    db.session.refresh(config)
    assert (config.MINLENGTH, config.MAXLENGTH, config.RIPMETHOD) == ("1", "2", "backup")
    # The settings page and every arm.yaml save serialise cfg.arm_config: a per-job edit must not leak there.
    assert {key: cfg.arm_config[key] for key in before} == before


def test_json_change_params_for_a_missing_job_is_not_a_500(ui):
    app, db = ui
    response = app.test_client().get("/json", headers=XHR, query_string={
        "mode": "change_job_params", "config_id": 999999, "DISCTYPE": "dvd"})
    assert response.status_code == 200
    assert response.get_json()["success"] is False
