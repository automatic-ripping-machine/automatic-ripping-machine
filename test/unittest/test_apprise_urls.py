"""Tests for the APPRISE_URLS setting used by arm.ripper.utils.notify()"""
from urllib.parse import urlsplit

import apprise
import pytest
import yaml

import arm.config.config as cfg
from arm.ripper import utils


@pytest.fixture
def notify_calls(monkeypatch):
    """Isolate notify() from the db, bash and network; record each Apprise.notify() call"""
    for key in ("ARM_NAME", "PB_KEY", "IFTTT_KEY", "PO_USER_KEY", "JSON_URL", "APPRISE", "BASH_SCRIPT"):
        monkeypatch.setitem(cfg.arm_config, key, "")
    monkeypatch.setitem(cfg.arm_config, "NOTIFY_JOBID", False)
    monkeypatch.setattr(utils, "database_adder", lambda *args, **kwargs: None)
    calls = []

    def fake_notify(self, body, title="", **kwargs):
        calls.append({"urls": sorted(server.url() for server in self), "body": body, "title": title})
        return True

    monkeypatch.setattr(apprise.Apprise, "notify", fake_notify)
    return calls


def test_apprise_urls_are_all_added(monkeypatch, notify_calls):
    monkeypatch.setitem(cfg.arm_config, "APPRISE_URLS",
                        "jsons://first.example.com/hook, jsons://second.example.org/hook")

    utils.notify(None, "title", "body")

    assert len(notify_calls) == 1
    urls = notify_calls[0]["urls"]
    assert len(urls) == 2
    assert {urlsplit(url).hostname for url in urls} == {"first.example.com", "second.example.org"}
    assert notify_calls[0]["title"] == "title"


def test_empty_apprise_urls_adds_nothing(monkeypatch, notify_calls):
    monkeypatch.setitem(cfg.arm_config, "APPRISE_URLS", "")

    utils.notify(None, "title", "body")

    # Unchanged behaviour: no services added (notify() may then be skipped entirely)
    assert len(notify_calls) <= 1
    assert all(call["urls"] == [] for call in notify_calls)


def test_apprise_urls_combine_with_existing_keys(monkeypatch, notify_calls):
    monkeypatch.setitem(cfg.arm_config, "JSON_URL", "https://existing.example.net/hook")
    monkeypatch.setitem(cfg.arm_config, "APPRISE_URLS", "jsons://extra.example.com/hook")

    utils.notify(None, "title", "body")

    assert len(notify_calls) == 1
    assert len(notify_calls[0]["urls"]) == 2


def test_invalid_apprise_url_is_reported_without_the_url(monkeypatch, notify_calls, caplog):
    # A Home Assistant URL without its access token can't be loaded
    host = "private-host.example.com"
    monkeypatch.setitem(cfg.arm_config, "APPRISE_URLS", f"jsons://ok.example.com/hook hassios://{host}")

    utils.notify(None, "title", "body")

    assert len(notify_calls[0]["urls"]) == 1
    arm_messages = [record.getMessage() for record in caplog.records if not record.name.startswith("apprise")]
    assert any("APPRISE_URLS" in message for message in arm_messages)
    assert not any(host in message for message in arm_messages)


def test_apprise_urls_round_trip_through_settings_save():
    from arm.ui import app
    from arm.ui import utils as ui_utils
    comments = ui_utils.generate_comments()
    urls = "jsons://token-value@example.com/hook, hassios://hass.example.com/token-value"

    with app.app_context(), app.test_request_context():
        saved = ui_utils.build_arm_cfg({"APPRISE_URLS": urls}, comments)

    assert yaml.safe_load(saved)["APPRISE_URLS"] == urls
