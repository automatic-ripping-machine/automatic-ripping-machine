"""Flash messages are escaped: request values shown in a flash must not run as script."""
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


PAYLOAD = "<script>alert(1)</script>"


def test_search_title_in_a_flash_message_is_escaped(ui):
    from arm.ui import utils as ui_utils

    app, db = ui
    ui_utils.arm_db_cfg()
    job = make_job(db)
    page = app.test_client().get("/list_titles", query_string={"title": PAYLOAD, "year": "1999",
                                                               "job_id": job.job_id}).get_data(as_text=True)
    assert "No search results found for" in page
    assert PAYLOAD not in page
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page


@pytest.mark.parametrize("base", ["base.html", "support/base_simple.html"])
def test_both_base_templates_escape_flash_messages(ui, base):
    from flask import flash, render_template_string

    app, db = ui
    with app.test_request_context("/"):
        flash(PAYLOAD, "danger")
        page = render_template_string(f"{{% extends '{base}' %}}")
    assert PAYLOAD not in page
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page
