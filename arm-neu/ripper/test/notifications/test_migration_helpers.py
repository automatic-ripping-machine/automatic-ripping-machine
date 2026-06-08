"""Tests for the legacy-config → channel-row translation helpers."""
import pytest


def test_translate_pb_key():
    from arm.notifications.migration_helpers import translate_legacy_config
    rows = translate_legacy_config({
        "PB_KEY": "abc123",
        "IFTTT_KEY": "",
        "PO_USER_KEY": "",
        "JSON_URL": "",
        "APPRISE": "",
        "BASH_SCRIPT": "",
        "NOTIFY_RIP": True,
        "NOTIFY_TRANSCODE": True,
    })
    pb = [r for r in rows if r["type"] == "apprise"
          and "pbul://" in r["config"]["url"]]
    assert len(pb) == 1
    assert pb[0]["config"]["url"] == "pbul://abc123"
    assert pb[0]["name"] == "Pushbullet (migrated)"


def test_translate_ifttt_with_event():
    from arm.notifications.migration_helpers import translate_legacy_config
    rows = translate_legacy_config({
        "PB_KEY": "", "IFTTT_KEY": "key123", "IFTTT_EVENT": "arm_event",
        "PO_USER_KEY": "", "JSON_URL": "", "APPRISE": "",
        "BASH_SCRIPT": "",
        "NOTIFY_RIP": True, "NOTIFY_TRANSCODE": True,
    })
    ifttt = [r for r in rows if "ifttt://" in r["config"].get("url", "")]
    assert len(ifttt) == 1
    assert ifttt[0]["config"]["url"] == "ifttt://key123@arm_event"


def test_translate_pover_both_keys():
    from arm.notifications.migration_helpers import translate_legacy_config
    rows = translate_legacy_config({
        "PB_KEY": "", "IFTTT_KEY": "",
        "PO_USER_KEY": "u1", "PO_APP_KEY": "a1",
        "JSON_URL": "", "APPRISE": "", "BASH_SCRIPT": "",
        "NOTIFY_RIP": True, "NOTIFY_TRANSCODE": True,
    })
    pover = [r for r in rows if "pover://" in r["config"].get("url", "")]
    assert len(pover) == 1
    assert pover[0]["config"]["url"] == "pover://u1@a1"


def test_translate_pover_skipped_when_user_key_blank():
    """If PO_USER_KEY is blank, skip even if PO_APP_KEY is set
    (mirrors the legacy notify() behavior)."""
    from arm.notifications.migration_helpers import translate_legacy_config
    rows = translate_legacy_config({
        "PB_KEY": "", "IFTTT_KEY": "",
        "PO_USER_KEY": "", "PO_APP_KEY": "a1",
        "JSON_URL": "", "APPRISE": "", "BASH_SCRIPT": "",
        "NOTIFY_RIP": True, "NOTIFY_TRANSCODE": True,
    })
    pover = [r for r in rows if "pover://" in r["config"].get("url", "")]
    assert len(pover) == 0


def test_translate_json_url_to_apprise_json_scheme():
    from arm.notifications.migration_helpers import translate_legacy_config
    rows = translate_legacy_config({
        "PB_KEY": "", "IFTTT_KEY": "", "PO_USER_KEY": "",
        "JSON_URL": "https://example.com/hook",
        "APPRISE": "", "BASH_SCRIPT": "",
        "NOTIFY_RIP": True, "NOTIFY_TRANSCODE": True,
    })
    j = [r for r in rows if r["config"].get("url", "").startswith("jsons://")]
    assert len(j) == 1
    assert j[0]["config"]["url"] == "jsons://example.com/hook"


def test_translate_json_url_plain_http_to_json_scheme():
    """A legacy plain-http JSON_URL becomes apprise's json:// scheme."""
    from arm.notifications.migration_helpers import translate_legacy_config
    plain = "http" + "://example.com/hook"
    rows = translate_legacy_config({
        "PB_KEY": "", "IFTTT_KEY": "", "PO_USER_KEY": "",
        "JSON_URL": plain,
        "APPRISE": "", "BASH_SCRIPT": "",
        "NOTIFY_RIP": True, "NOTIFY_TRANSCODE": True,
    })
    j = [r for r in rows if r["config"].get("url", "").startswith("json://")]
    assert len(j) == 1
    assert j[0]["config"]["url"] == "json://example.com/hook"


def test_translate_json_url_without_scheme_passes_through():
    """A JSON_URL that has no http(s) prefix is used verbatim."""
    from arm.notifications.migration_helpers import translate_legacy_config
    rows = translate_legacy_config({
        "PB_KEY": "", "IFTTT_KEY": "", "PO_USER_KEY": "",
        "JSON_URL": "json://already-a-scheme/hook",
        "APPRISE": "", "BASH_SCRIPT": "",
        "NOTIFY_RIP": True, "NOTIFY_TRANSCODE": True,
    })
    j = [r for r in rows if r["name"] == "JSON Webhook (migrated)"]
    assert len(j) == 1
    assert j[0]["config"]["url"] == "json://already-a-scheme/hook"


def test_translate_bash_script():
    from arm.notifications.migration_helpers import translate_legacy_config
    rows = translate_legacy_config({
        "PB_KEY": "", "IFTTT_KEY": "", "PO_USER_KEY": "",
        "JSON_URL": "", "APPRISE": "",
        "BASH_SCRIPT": "/opt/arm/scripts/notify.sh",
        "NOTIFY_RIP": True, "NOTIFY_TRANSCODE": True,
    })
    bash = [r for r in rows if r["type"] == "bash"]
    assert len(bash) == 1
    assert bash[0]["config"]["script_path"] == "/opt/arm/scripts/notify.sh"


def test_translate_apprise_yaml_path_skipped_when_missing(tmp_path):
    from arm.notifications.migration_helpers import translate_legacy_config
    rows = translate_legacy_config({
        "PB_KEY": "", "IFTTT_KEY": "", "PO_USER_KEY": "",
        "JSON_URL": "",
        "APPRISE": str(tmp_path / "nonexistent.yaml"),
        "BASH_SCRIPT": "",
        "NOTIFY_RIP": True, "NOTIFY_TRANSCODE": True,
    })
    apprise_from_yaml = [r for r in rows if r["name"].startswith("apprise:")]
    assert len(apprise_from_yaml) == 0


def test_translate_apprise_yaml_parses_known_keys(tmp_path):
    """If apprise.yaml contains entries, each non-empty value becomes
    a channel."""
    from arm.notifications.migration_helpers import translate_legacy_config
    yaml_path = tmp_path / "apprise.yaml"
    yaml_path.write_text(
        "urls:\n"
        "  - discord://abc/def\n"
        "  - tgram://bottoken/chatid\n"
    )
    rows = translate_legacy_config({
        "PB_KEY": "", "IFTTT_KEY": "", "PO_USER_KEY": "",
        "JSON_URL": "",
        "APPRISE": str(yaml_path),
        "BASH_SCRIPT": "",
        "NOTIFY_RIP": True, "NOTIFY_TRANSCODE": True,
    })
    yaml_rows = [r for r in rows if r["name"].startswith("apprise:")]
    assert len(yaml_rows) == 2


def test_translate_apprise_yaml_malformed_is_skipped(tmp_path):
    """A corrupt apprise.yaml is logged and skipped, not fatal — the
    rest of the legacy config still translates."""
    from arm.notifications.migration_helpers import translate_legacy_config
    yaml_path = tmp_path / "apprise.yaml"
    # Unbalanced bracket -> yaml.safe_load raises.
    yaml_path.write_text("urls: [discord://abc/def\n  bad: : :\n")
    rows = translate_legacy_config({
        "PB_KEY": "pbtoken", "IFTTT_KEY": "", "PO_USER_KEY": "",
        "JSON_URL": "",
        "APPRISE": str(yaml_path),
        "BASH_SCRIPT": "",
        "NOTIFY_RIP": True, "NOTIFY_TRANSCODE": True,
    })
    # No apprise:N rows from the broken file, but PB_KEY still migrated.
    yaml_rows = [r for r in rows if r["name"].startswith("apprise:")]
    assert len(yaml_rows) == 0
    assert any(r["name"] == "Pushbullet (migrated)" for r in rows)


def test_subscribed_events_from_notify_toggles():
    """NOTIFY_RIP=True → subscribed to started + rip_complete;
    NOTIFY_TRANSCODE=True → subscribed to transcode_complete.
    All migrated channels also subscribe to job.failed."""
    from arm.notifications.migration_helpers import translate_legacy_config
    rows = translate_legacy_config({
        "PB_KEY": "abc", "IFTTT_KEY": "", "PO_USER_KEY": "",
        "JSON_URL": "", "APPRISE": "", "BASH_SCRIPT": "",
        "NOTIFY_RIP": True, "NOTIFY_TRANSCODE": True,
    })
    assert len(rows) == 1
    subs = set(rows[0]["subscribed_events"])
    assert "job.started" in subs
    assert "job.rip_complete" in subs
    assert "job.transcode_complete" in subs
    assert "job.failed" in subs


def test_subscribed_events_with_notify_rip_only():
    from arm.notifications.migration_helpers import translate_legacy_config
    rows = translate_legacy_config({
        "PB_KEY": "abc", "IFTTT_KEY": "", "PO_USER_KEY": "",
        "JSON_URL": "", "APPRISE": "", "BASH_SCRIPT": "",
        "NOTIFY_RIP": True, "NOTIFY_TRANSCODE": False,
    })
    subs = set(rows[0]["subscribed_events"])
    assert "job.started" in subs
    assert "job.rip_complete" in subs
    assert "job.transcode_complete" not in subs
    assert "job.failed" in subs


def test_empty_config_yields_no_rows():
    from arm.notifications.migration_helpers import translate_legacy_config
    rows = translate_legacy_config({
        "PB_KEY": "", "IFTTT_KEY": "", "PO_USER_KEY": "",
        "JSON_URL": "", "APPRISE": "", "BASH_SCRIPT": "",
        "NOTIFY_RIP": False, "NOTIFY_TRANSCODE": False,
    })
    assert rows == []
