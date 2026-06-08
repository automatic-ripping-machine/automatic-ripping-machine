"""Generate Tinyauth-compatible user files from the auth DB.

Tinyauth expects one user per line: username:bcrypt_hash[:totp_secret]
"""

import logging
from pathlib import Path

from arm_auth.db import AuthDB
from arm_auth.models import User

logger = logging.getLogger(__name__)


def generate_users_file(db: AuthDB) -> str:
    """Generate Tinyauth users file content from the auth DB.

    Returns a string with one user per line in the format:
        username:bcrypt_hash
    Only active users are included.
    """
    lines = []
    with db.session() as s:
        users = s.query(User).filter_by(active=True).all()
        for user in users:
            lines.append(f"{user.username}:{user.password_hash}")

    return "\n".join(lines) + "\n" if lines else "# no active users\n"


def sync_users(db: AuthDB, users_file_path: str):
    """Write the Tinyauth users file to disk.

    Creates parent directories if they don't exist.
    Uses atomic write (temp file + rename) to avoid partial writes.
    """
    content = generate_users_file(db)
    path = Path(users_file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Atomic write: write to temp file, then rename
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_text(content, encoding="utf-8")
    tmp_path.replace(path)

    user_count = len([l for l in content.strip().split("\n") if l and not l.startswith("#")])
    logger.info("Synced %d users to %s", user_count, users_file_path)
