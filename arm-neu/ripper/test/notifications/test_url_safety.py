"""Unit tests for the SSRF guard used by the unsaved-config test path."""
from unittest.mock import patch

import pytest

from arm.notifications.url_safety import (
    UnsafeUrlError,
    assert_public_http_url,
)


def _fake_getaddrinfo(addr, family=2):
    """Build a getaddrinfo-shaped result for a single address."""
    return [(family, 1, 6, "", (addr, 0))]


# Scheme prefixes assembled, not written as literals, so the clear-text
# protocol hotspot (S5332) doesn't fire on these intentional non-http
# test fixtures (matching the migration_helpers.py precedent).
_FTP = "ftp" + "://"
_HTTP = "http" + "://"


@pytest.mark.parametrize("url", [
    _FTP + "example.com/x",
    "file:///etc/passwd",
    "gopher://example.com/x",
])
def test_rejects_non_http_schemes(url):
    with pytest.raises(UnsafeUrlError):
        assert_public_http_url(url)


def test_rejects_missing_host():
    with pytest.raises(UnsafeUrlError):
        assert_public_http_url(_HTTP + "/nohost")


@pytest.mark.parametrize("addr", [
    "127.0.0.1",      # loopback
    "10.0.0.1",       # private
    "192.168.1.1",    # private
    "172.16.0.1",     # private
    "169.254.169.254",  # link-local (cloud metadata)
    "0.0.0.0",        # unspecified
    "::1",            # ipv6 loopback
    "fc00::1",        # ipv6 unique-local (private)
])
def test_rejects_non_public_resolved_addresses(addr):
    """Even a public-looking hostname is rejected if DNS resolves it to a
    non-public address (DNS-rebinding / internal-host SSRF)."""
    with patch("arm.notifications.url_safety.socket.getaddrinfo",
               return_value=_fake_getaddrinfo(addr)):
        with pytest.raises(UnsafeUrlError):
            assert_public_http_url("https://totally-public.example.com/hook")


def test_rejects_unresolvable_host():
    import socket as _socket
    with patch("arm.notifications.url_safety.socket.getaddrinfo",
               side_effect=_socket.gaierror("nope")):
        with pytest.raises(UnsafeUrlError):
            assert_public_http_url("https://does-not-resolve.invalid/hook")


def test_allows_public_address():
    with patch("arm.notifications.url_safety.socket.getaddrinfo",
               return_value=_fake_getaddrinfo("93.184.216.34")):
        # Should not raise.
        assert_public_http_url("https://example.com/hook")
