#!/usr/bin/env python3
import os
import sys
import types
from unittest.mock import MagicMock

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

if "ARM_CONFIG_FILE" not in os.environ:
    os.environ["ARM_CONFIG_FILE"] = os.path.join(repo_root, "setup/arm.yaml")


class MockModule(types.ModuleType):
    def __init__(self, name):
        super().__init__(name)
        self.__path__ = []

    def __getattr__(self, name):
        if name in ("__file__", "__path__", "__spec__"):
            return None
        mock = MagicMock()
        setattr(self, name, mock)
        return mock


# Mock heavy/external dependencies if not installed in current environment
for dep in [
    "apprise", "flask", "flask.logging", "flask.views", "flask_login", "flask_sqlalchemy", "sqlalchemy",
    "sqlalchemy.orm", "sqlalchemy.ext", "sqlalchemy.ext.hybrid", "flask_migrate", "flask_cors", "flask_wtf",
    "wtforms", "wtforms.validators", "netifaces", "bcrypt", "requests", "psutil", "pyudev", "pydvdid", "xmltodict",
    "alembic", "alembic.script", "alembic.config", "sqlalchemy.sql", "sqlalchemy.sql.schema", "sqlalchemy.exc",
    "discid", "musicbrainzngs", "werkzeug", "werkzeug.utils", "werkzeug.routing", "prettytable"
]:
    if dep not in sys.modules:
        try:
            __import__(dep)
        except ImportError:
            sys.modules[dep] = MockModule(dep)

class DummyModel: pass
class DummyUserMixin: pass
if hasattr(sys.modules.get("flask_login"), "UserMixin"):
    sys.modules["flask_login"].UserMixin = DummyUserMixin
if hasattr(sys.modules.get("sqlalchemy.exc"), "SQLAlchemyError"):
    sys.modules["sqlalchemy.exc"].SQLAlchemyError = Exception
if hasattr(sys.modules.get("werkzeug.routing"), "ValidationError"):
    sys.modules["werkzeug.routing"].ValidationError = Exception

db_mock = MockModule("arm.ui.db")
db_mock.Model = DummyModel
if "arm.ui" not in sys.modules or not hasattr(sys.modules["arm.ui"], "db"):
    sys.modules["arm.ui"] = MockModule("arm.ui")
    sys.modules["arm.ui"].__path__ = [os.path.join(repo_root, "arm/ui")]
    sys.modules["arm.ui"].db = db_mock
