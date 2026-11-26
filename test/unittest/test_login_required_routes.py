"""Admin-only routes need a login, and login/password change never 500."""
import secrets

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


@pytest.fixture
def login_enabled(ui, monkeypatch):
    import arm.config.config as cfg
    from arm.models.user import User
    from arm.ui import utils as ui_utils

    app, db = ui
    monkeypatch.setitem(app.config, "LOGIN_DISABLED", False)
    monkeypatch.setitem(cfg.arm_config, "DISABLE_LOGIN", False)
    monkeypatch.setitem(app.config, "WTF_CSRF_ENABLED", False)
    monkeypatch.setattr(ui_utils, "arm_db_check", lambda: {"db_exists": True, "db_current": True})
    User.query.delete()
    db.session.commit()
    yield app, db
    User.query.delete()
    db.session.commit()


# Generated per run so no credential literal lives in the test.
ADMIN_PASSWORD = secrets.token_urlsafe(12)
NEW_PASSWORD = secrets.token_urlsafe(12)


def redirects_to_login(response):
    return response.status_code == 302 and response.headers["Location"].endswith("/login")


@pytest.mark.parametrize("path", ["/systemdrivescan", "/updatesysinfo"])
def test_state_changing_settings_links_need_a_login(login_enabled, path, monkeypatch):
    from arm.ui.settings import DriveUtils

    app, db = login_enabled
    monkeypatch.setattr(DriveUtils, "drives_update", lambda *a, **k: pytest.fail("ran without a login"))
    assert redirects_to_login(app.test_client().get(path))


def test_database_update_is_an_admin_action_once_the_database_is_current(login_enabled, monkeypatch):
    from arm.ui import utils as ui_utils

    app, db = login_enabled
    monkeypatch.setattr(ui_utils, "arm_db_migrate", lambda: pytest.fail("anonymous request copied the database"))
    assert redirects_to_login(app.test_client().post("/dbupdate", data={"dbfix": "migrate"}))


def test_login_without_an_admin_account_is_refused_not_a_500(login_enabled):
    app, db = login_enabled
    response = app.test_client().post("/login", data={"username": "admin", "password": ADMIN_PASSWORD})
    assert response.status_code == 200
    assert "Something isn" in response.get_data(as_text=True)


def make_admin(db):
    import bcrypt
    from arm.models.user import User

    salt = bcrypt.gensalt(4)
    db.session.add(User(email="admin", password=bcrypt.hashpw(ADMIN_PASSWORD.encode(), salt), hashed=salt))
    db.session.commit()


def test_login_and_password_change(login_enabled):
    app, db = login_enabled
    make_admin(db)
    client = app.test_client()
    assert client.post("/login", data={"username": "admin", "password": "x" + ADMIN_PASSWORD}).status_code == 200
    assert client.post("/login", data={"username": "admin", "password": ADMIN_PASSWORD}).status_code == 302
    # an unknown account name used to raise AttributeError (500)
    response = client.post("/update_password", data={"username": "nobody", "old_password": ADMIN_PASSWORD,
                                                     "new_password": NEW_PASSWORD})
    assert response.status_code == 200
    assert "does not match" in response.get_data(as_text=True)
    response = client.post("/update_password", data={"username": "admin", "old_password": ADMIN_PASSWORD,
                                                     "new_password": NEW_PASSWORD})
    assert response.status_code == 302
    client.get("/logout")
    assert client.post("/login", data={"username": "admin", "password": ADMIN_PASSWORD}).status_code == 200
    assert client.post("/login", data={"username": "admin", "password": NEW_PASSWORD}).status_code == 302
