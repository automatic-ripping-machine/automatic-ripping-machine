"""Test and job notifications use the same ARM UI address (#1769)."""

from types import SimpleNamespace

import pytest

import arm.config.config as cfg


@pytest.mark.parametrize("base", ["", "https://arm.example.lan/"])
def test_test_notification_uses_the_job_notification_address(monkeypatch, base):
    from arm.ripper import utils
    from arm.ui import app
    from arm.ui.settings import settings

    monkeypatch.setitem(cfg.arm_config, "UI_BASE_URL", base)
    monkeypatch.setitem(cfg.arm_config, "WEBSERVER_PORT", 8080)
    monkeypatch.setattr(utils, "check_ip", lambda: "192.0.2.7")
    sent = []
    monkeypatch.setattr(utils, "notify", lambda job, title, body: sent.append(body))
    monkeypatch.setattr(utils, "database_adder", lambda value: None)
    monkeypatch.setitem(app.config, "LOGIN_DISABLED", True)
    with app.test_request_context("/testapprise"):
        settings.testapprise()
    job = SimpleNamespace(job_id=1, label="L", title="T", disctype="dvd",
                          config=SimpleNamespace(WEBSERVER_PORT=8080, MAINFEATURE=False))
    utils.notify_entry(job)

    expected = base.rstrip("/") or "http://192.0.2.7:8080"
    assert sent[0].endswith("Server URL: " + expected)
    assert expected + "/jobdetail?job_id=1" in sent[1]
