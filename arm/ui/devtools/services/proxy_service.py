"""
Devtools service - proxied HTTP requests to the local ARM UI.

Lets an agent call ARM's own endpoints (like the /json feed) through the
devtools API without a session cookie. Localhost only - no external URLs.
"""
from __future__ import annotations

from typing import Any

import requests

from config import config as cfg


def make_http_request(method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Make an HTTP request to the local ARM UI.

    Args:
        method: HTTP method (GET or POST)
        path: URL path on the local UI, e.g. /json?mode=joblist
        body: optional JSON body for POST requests

    Returns:
        dict: status code, content type and response body
    """
    method = method.upper()
    if method not in ("GET", "POST"):
        raise ValueError(f"Unsupported method '{method}' - only GET and POST are proxied")
    port = cfg.arm_config.get("WEBSERVER_PORT", 8080)
    url = f"http://127.0.0.1:{port}{path if path.startswith('/') else '/' + path}"
    try:
        if method == "GET":
            response = requests.get(url, timeout=30)
        else:
            response = requests.post(url, json=body or {}, timeout=30)
    except requests.RequestException as error:
        raise ValueError(f"could not reach {url}: {error}") from error
    content_type = response.headers.get("Content-Type", "")
    if "json" in content_type:
        payload: Any = response.json()
    else:
        payload = response.text[:10000]
    return {"status_code": response.status_code, "content_type": content_type, "body": payload}
