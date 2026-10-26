"""Routes that change state answer only a POST carrying the page's CSRF token, never a plain GET.

A link or image on another site is a GET that carries the session cookie, so a GET must not change anything.
"""
import datetime
import re

import pytest


@pytest.fixture
def ui(monkeypatch):
    import arm.config.config as cfg
    from arm.ui import app, db, utils as ui_utils
    import arm.ui.routes  # noqa: F401 -- register the blueprints as runui does

    monkeypatch.setattr(ui_utils, "metadata_selector", lambda *args, **kwargs: None)
    monkeypatch.setitem(app.config, "TESTING", True)
    monkeypatch.setitem(app.config, "LOGIN_DISABLED", True)
    # /json's own login check reads arm.yaml's DISABLE_LOGIN
    monkeypatch.setitem(cfg.arm_config, "DISABLE_LOGIN", True)
    with app.app_context():
        db.create_all()
        yield app, db
        db.session.rollback()
        db.session.remove()


@pytest.fixture
def calls(monkeypatch):
    """Replace the side effect behind each route with a recorder (no drives, no Apprise, no network)"""
    from arm.ui import json_api, utils as ui_utils
    from arm.ui.auth import auth
    from arm.ui.settings import settings, DriveUtils
    from arm.models.system_info import SystemInfo

    seen = []

    def recorder(name, result=None):
        def record(*args, **kwargs):
            seen.append(name)
            return {"mode": name, "success": True} if result is None else result
        return record

    monkeypatch.setattr(DriveUtils, "drives_update", recorder("drives_update", 0))
    monkeypatch.setattr(settings.ripper_utils, "notify", recorder("notify", True))

    def read_system(system):
        seen.append("sysinfo")
        system.cpu, system.mem_total = "test cpu", 1

    monkeypatch.setattr(SystemInfo, "get_cpu_info", read_system)
    monkeypatch.setattr(SystemInfo, "get_memory", lambda system: None)
    monkeypatch.setattr(auth, "logout_user", recorder("logout_user", True))
    monkeypatch.setattr(ui_utils, "generate_file_list", recorder("import_movies", []))
    for name in ("delete_job", "abandon_job", "change_job_params", "read_notification", "restart_ui"):
        monkeypatch.setattr(json_api, name, recorder(name))
    for name in ("fix_permissions", "send_to_remote_db"):
        monkeypatch.setattr(ui_utils, name, recorder(name))
    return seen


def make_job(db, **values):
    from arm.models.job import Job

    job = Job.__mapper__.class_manager.new_instance()
    job.status, job.devpath, job.crc_id = "success", "/dev/sr-test", "crc-test"
    job.disctype, job.title, job.year, job.video_type = "dvd", "Some Movie", "2001", "movie"
    job.start_time, job.ejected = datetime.datetime.now(), False
    for name, value in values.items():
        setattr(job, name, value)
    db.session.add(job)
    db.session.commit()
    return job


def page_token(client):
    """The CSRF token every page carries in its head, as the UI's scripts read it"""
    page = client.get("/notificationview").get_data(as_text=True)
    match = re.search(r'<meta name="csrf-token" content="([^"]+)"', page)
    assert match, "no csrf-token meta tag in the page head"
    return match.group(1)


XHR = {"X-Requested-With": "XMLHttpRequest"}

PLAIN_ROUTES = [
    ("/systemdrivescan", "drives_update"),
    ("/testapprise", "notify"),
    ("/updatesysinfo", "sysinfo"),
    ("/logout", "logout_user"),
    ("/import_movies", "import_movies"),
]

JSON_MODES = [
    ("delete", "delete_job"),
    ("abandon", "abandon_job"),
    ("fixperms", "fix_permissions"),
    ("send_item", "send_to_remote_db"),
    ("change_job_params", "change_job_params"),
    ("read_notification", "read_notification"),
]


@pytest.mark.parametrize("path, effect", PLAIN_ROUTES)
def test_a_get_changes_nothing(ui, calls, path, effect):
    app, db = ui
    # e.g. <img src="http://arm:8080/systemdrivescan"> on another site
    response = app.test_client().get(path)
    assert response.status_code == 405
    assert effect not in calls


@pytest.mark.parametrize("path, effect", PLAIN_ROUTES)
def test_a_post_without_the_token_is_refused(ui, calls, path, effect):
    app, db = ui
    response = app.test_client().post(path)
    assert response.status_code == 400
    assert effect not in calls


@pytest.mark.parametrize("path, effect", PLAIN_ROUTES)
def test_a_post_with_the_page_token_works(ui, calls, path, effect):
    app, db = ui
    client = app.test_client()
    response = client.post(path, data={"csrf_token": page_token(client)})
    assert response.status_code in (200, 302)
    assert effect in calls


@pytest.mark.parametrize("mode, effect", JSON_MODES)
def test_json_state_change_is_refused_as_a_get(ui, calls, mode, effect):
    app, db = ui
    # Even with the header the UI used to send: a GET is never a change
    response = app.test_client().get("/json", query_string={"mode": mode, "job": 1}, headers=XHR)
    assert response.status_code == 405
    assert effect not in calls


@pytest.mark.parametrize("mode, effect", JSON_MODES)
def test_json_state_change_needs_the_token(ui, calls, mode, effect):
    app, db = ui
    client = app.test_client()
    response = client.post("/json", data={"mode": mode, "job": 1}, headers=XHR)
    assert response.status_code == 400
    assert effect not in calls
    response = client.post("/json", data={"mode": mode, "job": 1}, headers={"X-CSRFToken": page_token(client)})
    assert response.status_code == 200
    assert effect in calls


def test_json_reads_still_work_as_a_get(ui):
    app, db = ui
    response = app.test_client().get("/json", query_string={"mode": "joblist"})
    assert response.status_code == 200


def test_updatetitle_only_changes_the_job_on_a_post(ui):
    from arm.models.job import Job

    app, db = ui
    job_id = make_job(db).job_id
    client = app.test_client()
    new = {"job_id": job_id, "title": "Other Movie", "year": "1999", "imdbID": "tt0000001", "type": "movie"}
    assert client.get("/updatetitle", query_string=new).status_code == 405
    db.session.expire_all()
    assert db.session.get(Job, job_id).title == "Some Movie"
    assert client.post("/updatetitle", data=dict(new, csrf_token=page_token(client))).status_code == 302
    db.session.expire_all()
    assert db.session.get(Job, job_id).title == "Other Movie"


def test_custom_title_get_only_shows_the_form(ui):
    from arm.models.job import Job

    app, db = ui
    job_id = make_job(db).job_id
    client = app.test_client()
    response = client.get("/customTitle", query_string={"job_id": job_id, "title": "Other Movie", "year": "1999"})
    assert response.status_code == 200
    db.session.expire_all()
    assert db.session.get(Job, job_id).title == "Some Movie"
    response = client.post("/customTitle", data={"job_id": job_id, "title": "Other Movie", "year": "1999",
                                                 "csrf_token": page_token(client)})
    assert response.status_code == 302
    db.session.expire_all()
    assert db.session.get(Job, job_id).title == "Other Movie"


def test_notifications_are_only_cleared_by_a_post(ui):
    from arm.models.notifications import Notifications

    app, db = ui
    notification = Notifications("Test", "A test notification")
    db.session.add(notification)
    db.session.commit()
    notify_id = notification.id
    client = app.test_client()
    assert client.get("/notificationclose").status_code == 405
    db.session.expire_all()
    assert not db.session.get(Notifications, notify_id).cleared
    assert client.post("/notificationclose", data={"csrf_token": page_token(client)}).status_code == 302
    db.session.expire_all()
    assert db.session.get(Notifications, notify_id).cleared


def test_read_notification_from_the_ui_marks_it_seen(ui):
    from arm.models.notifications import Notifications

    app, db = ui
    notification = Notifications("Test", "A test notification")
    db.session.add(notification)
    db.session.commit()
    notify_id = notification.id
    client = app.test_client()
    # What common.js sends when a toast closes
    data = client.post("/json", data={"mode": "read_notification", "notify_id": notify_id},
                       headers={"X-CSRFToken": page_token(client)}).get_json()
    assert data["success"] is True
    db.session.expire_all()
    assert db.session.get(Notifications, notify_id).seen


def test_nav_logs_out_with_a_form(ui):
    app, db = ui
    page = app.test_client().get("/notificationview").get_data(as_text=True)
    form = re.search(r'<form action="/logout" method="post"[^>]*>(.*?)</form>', page, re.S)
    assert form, "the nav's log out is not a POST form"
    assert 'name="csrf_token"' in form.group(1)
