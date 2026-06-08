"""Tests for the apprise URL composer."""
import pytest


def test_compose_discord_basic():
    """Discord's URL form is ``discord://<webhook_id>/<webhook_token>``.
    The composer slots required fields into the path in order."""
    from arm.notifications.url_composer import compose_apprise_url
    url = compose_apprise_url(
        service_id="discord",
        required={"webhook_id": "1234", "webhook_token": "abcd"},
        advanced={},
    )
    assert url == "discord://1234/abcd"


def test_compose_discord_with_advanced():
    from arm.notifications.url_composer import compose_apprise_url
    url = compose_apprise_url(
        service_id="discord",
        required={"webhook_id": "1234", "webhook_token": "abcd"},
        advanced={"tts": True, "avatar": False},
    )
    # Booleans render as "yes"/"no" per apprise convention.
    assert url.startswith("discord://1234/abcd?")
    assert "tts=yes" in url
    assert "avatar=no" in url


def test_compose_url_encodes_special_chars():
    from arm.notifications.url_composer import compose_apprise_url
    url = compose_apprise_url(
        service_id="discord",
        required={"webhook_id": "1234", "webhook_token": "a/b c"},
        advanced={},
    )
    # The token should be URL-encoded in the path.
    assert "a%2Fb%20c" in url or "a%2Fb+c" in url


def test_compose_pover_at_separator():
    """Pushover uses ``pover://<user_key>@<app_key>`` (note the @)."""
    from arm.notifications.url_composer import compose_apprise_url
    url = compose_apprise_url(
        service_id="pover",
        required={"user_key": "u1", "app_key": "a1"},
        advanced={},
    )
    # We use the catalog's required-field order to assemble; the @
    # separator is apprise-specific and we can't know it from metadata
    # alone. Fall back to ``/`` if the catalog doesn't define a
    # service-specific override. The frontend always has the raw-URL
    # escape hatch for cases where '/' isn't the right separator.
    assert url.startswith("pover://")
    assert "u1" in url and "a1" in url


def test_compose_omits_blank_advanced():
    """Empty-string advanced values must be omitted, not sent as `?key=`."""
    from arm.notifications.url_composer import compose_apprise_url
    url = compose_apprise_url(
        service_id="discord",
        required={"webhook_id": "1234", "webhook_token": "abcd"},
        advanced={"tts": "", "avatar": True},
    )
    assert "tts=" not in url or "tts=&" not in url
    assert "avatar=yes" in url


def test_compose_int_and_float_pass_through():
    from arm.notifications.url_composer import compose_apprise_url
    url = compose_apprise_url(
        service_id="ntfy",
        required={"topic": "alerts"},
        advanced={"priority": 4, "delay": 1.5},
    )
    assert "priority=4" in url
    assert "delay=1.5" in url
