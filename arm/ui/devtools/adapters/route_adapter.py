"""
Adapter for internally rendering ARM routes.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any

from flask import current_app


@contextmanager
def _temporary_app_config(overrides: dict[str, Any]):
    """
    Temporarily apply Flask config overrides, restoring them afterwards.

    Args:
        overrides: dict of config keys and values to apply
    """
    original = {key: current_app.config.get(key) for key in overrides}
    try:
        current_app.config.update(overrides)
        yield
    finally:
        for key, value in original.items():
            current_app.config[key] = value


@contextmanager
def _login_guard_disabled():
    """
    Temporarily disable Flask-Login's login_required check.

    ARM's @login_required decorators do not honour LOGIN_DISABLED, so
    rendering an authenticated page through the test client needs
    Flask-Login's own disable flag.
    """
    login_manager = getattr(current_app, "login_manager", None)
    if login_manager is None:
        yield
        return
    original = login_manager._login_disabled
    try:
        login_manager._login_disabled = True
        yield
    finally:
        login_manager._login_disabled = original


def resolve_route(path: str, method: str = "GET") -> tuple[str | None, dict[str, Any]]:
    """
    Resolve a path to an endpoint name and route arguments.

    Args:
        path: URL path to resolve
        method: HTTP method

    Returns:
        tuple: (endpoint name, view arguments) or (None, {})
    """
    adapter = current_app.url_map.bind("localhost")
    try:
        endpoint, values = adapter.match(path, method=method)
        return endpoint, dict(values)
    except Exception:
        return None, {}


def fetch_path(
    path: str,
    *,
    method: str = "GET",
    query_string: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
    follow_redirects: bool = True,
) -> dict[str, Any]:
    """
    Render a route through Flask's internal test client.

    Renders with login and CSRF disabled so any page can be inspected
    without a session.

    Args:
        path: URL path to render
        method: HTTP method (default GET)
        query_string: optional query parameters
        json_body: optional JSON body for POST requests
        follow_redirects: follow redirects (default True)

    Returns:
        dict: path, status_code, endpoint, view_args, html, content_type, headers
    """
    query_string = query_string or {}
    endpoint, view_args = resolve_route(path, method=method)
    # TESTING forces the client to render error pages instead of raising, so a
    # crashing ARM page yields a 500 snapshot rather than killing the call.
    with _temporary_app_config({
        "LOGIN_DISABLED": True,
        "WTF_CSRF_ENABLED": False,
        "TESTING": True,
        "PROPAGATE_EXCEPTIONS": False,
    }), _login_guard_disabled():
        with current_app.test_client() as client:
            caller = client.get if method.upper() == "GET" else client.post
            response = caller(
                path,
                query_string=query_string,
                json=json_body,
                follow_redirects=follow_redirects,
            )
    resolved_endpoint, resolved_args = resolve_route(response.request.path, method="GET")
    return {
        "path": response.request.path,
        "status_code": response.status_code,
        "endpoint": resolved_endpoint or endpoint,
        "view_args": resolved_args or view_args,
        "html": response.get_data(as_text=True),
        "content_type": response.content_type,
        "headers": dict(response.headers),
    }
