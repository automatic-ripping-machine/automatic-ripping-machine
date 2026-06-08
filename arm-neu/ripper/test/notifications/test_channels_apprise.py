"""Tests for the apprise channel sender."""
from unittest.mock import patch, MagicMock

import pytest


def test_send_apprise_returns_success_when_apprise_succeeds():
    """If apprise.Apprise().notify(...) returns True, send returns (True, None)."""
    from arm.notifications.channels.apprise import send_apprise

    fake = MagicMock()
    fake.add.return_value = True
    fake.notify.return_value = True
    with patch("arm.notifications.channels.apprise.apprise.Apprise",
               return_value=fake):
        ok, error = send_apprise(url="discord://x/y", title="T", body="B")
    assert ok is True
    assert error is None
    fake.add.assert_called_once_with("discord://x/y")
    fake.notify.assert_called_once_with(body="B", title="T")


def test_send_apprise_returns_terminal_failure_when_url_rejected():
    """apprise.add() returning False means apprise couldn't parse the URL —
    that's a terminal failure (retrying won't help)."""
    from arm.notifications.channels.apprise import send_apprise, AppriseSendError

    fake = MagicMock()
    fake.add.return_value = False
    with patch("arm.notifications.channels.apprise.apprise.Apprise",
               return_value=fake):
        ok, error = send_apprise(url="garbage://x", title="T", body="B")
    assert ok is False
    assert error is not None
    assert "URL" in error or "url" in error


def test_send_apprise_returns_failure_when_notify_returns_false():
    """If notify() returns False the send failed — treat as transient
    so the dispatcher can retry."""
    from arm.notifications.channels.apprise import send_apprise

    fake = MagicMock()
    fake.add.return_value = True
    fake.notify.return_value = False
    with patch("arm.notifications.channels.apprise.apprise.Apprise",
               return_value=fake):
        ok, error = send_apprise(url="discord://x/y", title="T", body="B")
    assert ok is False
    assert error is not None


def test_send_apprise_catches_exceptions():
    """Any exception from apprise should be caught and returned as an
    error string, never propagated."""
    from arm.notifications.channels.apprise import send_apprise

    fake = MagicMock()
    fake.add.side_effect = RuntimeError("library exploded")
    with patch("arm.notifications.channels.apprise.apprise.Apprise",
               return_value=fake):
        ok, error = send_apprise(url="discord://x/y", title="T", body="B")
    assert ok is False
    assert "library exploded" in error
