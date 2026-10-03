"""
Devtools service - Flask route listing.
"""
from __future__ import annotations

from typing import Any

from flask import current_app


def list_routes() -> dict[str, Any]:
    """
    List all registered Flask routes with methods and endpoints.

    Returns:
        dict: route count and sorted route list
    """
    routes = []
    for rule in sorted(current_app.url_map.iter_rules(), key=lambda r: r.rule):
        routes.append({
            "path": rule.rule,
            "methods": sorted((rule.methods or set()) - {"HEAD", "OPTIONS"}),
            "endpoint": rule.endpoint,
        })
    return {"count": len(routes), "routes": routes}
