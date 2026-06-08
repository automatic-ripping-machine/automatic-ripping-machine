"""Database Models
"""

from .alembic_version import AlembicVersion  # noqa F401
from .app_state import AppState  # noqa F401
from .config import Config  # noqa F401
from .expected_title import ExpectedTitle  # noqa F401
from .job import Job, JobState  # noqa F401
from .notifications import Notifications  # noqa F401
from .system_drives import SystemDrives  # noqa F401
from .system_info import SystemInfo  # noqa F401
from .track import Track  # noqa F401
from .ui_settings import UISettings  # noqa F401
from .user import User  # noqa F401

# Notifications module models — imported here so alembic's
# `import arm.models` populates db.metadata with them.
import arm.notifications.models  # noqa: F401
