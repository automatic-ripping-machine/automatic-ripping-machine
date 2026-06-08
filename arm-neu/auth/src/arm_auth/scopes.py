"""Permission scopes and default group definitions.

Scopes are string constants that gate access to specific actions.
Groups bundle scopes together for user-facing simplicity.
"""

# Meta-scope: grants all permissions
WILDCARD = "*"

# All defined scopes (wildcard excluded — it's a meta-scope)
ALL_SCOPES = {
    "jobs:read",
    "jobs:write",
    "logs:read",
    "settings:read",
    "settings:write",
    "users:read",
    "users:manage",
    "notifications:read",
    "transcode:read",
    "transcode:write",
}

# Default groups seeded on first init.
DEFAULT_GROUPS = {
    "admin": {
        "scopes": ["*"],
        "description": "Full access — manage users, settings, and all operations",
    },
    "user": {
        "scopes": [
            "jobs:read",
            "jobs:write",
            "logs:read",
            "settings:read",
            "notifications:read",
            "transcode:read",
            "transcode:write",
        ],
        "description": "Standard user — can use the system but not manage users or settings",
    },
}
