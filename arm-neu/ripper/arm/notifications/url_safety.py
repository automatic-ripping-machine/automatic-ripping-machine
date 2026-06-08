"""SSRF guard for request-controlled outbound URLs.

The dispatcher trusts URLs that an operator has already committed to the
DB (saved channels). The "test an unsaved config" path is different: the
URL comes straight from an HTTP request body, so a caller could point the
server at ``http://169.254.169.254/...`` or an internal service. This
module rejects such URLs before any outbound request is made.

Only used on the unsaved-test path. Saved channels stay unrestricted.
"""
import ipaddress
import socket
from urllib.parse import urlparse

_ALLOWED_SCHEMES = {"http", "https"}


class UnsafeUrlError(ValueError):
    """Raised when a request-supplied URL would target a non-public host."""


def _addr_is_public(addr: str) -> bool:
    ip = ipaddress.ip_address(addr)
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def assert_public_http_url(url: str) -> None:
    """Reject a URL whose host resolves to a non-public address.

    Requires an ``http``/``https`` scheme and a hostname, then resolves
    the host and rejects if *any* resolved address is private, loopback,
    link-local, reserved, multicast, or unspecified. Raises
    :class:`UnsafeUrlError` on any failure.
    """
    parsed = urlparse(url)
    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        raise UnsafeUrlError("URL must use http or https")
    host = parsed.hostname
    if not host:
        raise UnsafeUrlError("URL has no host")

    try:
        infos = socket.getaddrinfo(host, parsed.port or None,
                                   proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise UnsafeUrlError(f"could not resolve host: {host}") from exc

    addrs = {info[4][0] for info in infos}
    if not addrs:
        raise UnsafeUrlError(f"could not resolve host: {host}")
    for addr in addrs:
        if not _addr_is_public(addr):
            raise UnsafeUrlError(
                f"host {host} resolves to a non-public address"
            )
