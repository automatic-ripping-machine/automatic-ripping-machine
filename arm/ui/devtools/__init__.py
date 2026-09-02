"""
Automatic Ripping Machine - User Interface (UI)
    Developer JSON API

A dev-gated JSON API exposing ARM state, logs, database and system
information to developer tooling - scripts, CI or coding agents via MCP.

The API is disabled by default; enable it with ENABLE_DEVTOOLS in arm.yaml.
All endpoints live under /__devtools and return a stable JSON envelope.
"""
from flask import Blueprint


def create_blueprint() -> Blueprint:
    """
    Create the devtools blueprint and register routes lazily.

    Returns:
        Blueprint: the devtools blueprint, mounted under /__devtools
    """
    blueprint = Blueprint("devtools", __name__, url_prefix="/__devtools")

    from ui.devtools.routes import register_routes

    register_routes(blueprint)

    # Dev-only JSON endpoints; exempt them from the main app CSRF layer.
    try:
        from ui.ui_setup import csrf

        csrf.exempt(blueprint)
    except Exception:
        pass

    return blueprint
