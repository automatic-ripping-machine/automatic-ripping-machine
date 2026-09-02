"""
Devtools service - ARM database model querying.
"""
from __future__ import annotations

from typing import Any

from ui.devtools.serializer import serialize_model

_MODEL_REGISTRY: dict[str, Any] | None = None


def _get_registry() -> dict[str, Any]:
    """
    Lazily build the v3 model registry (single MySQL database).

    Returns:
        dict: model name to model class
    """
    global _MODEL_REGISTRY
    if _MODEL_REGISTRY is None:
        from models.alembic_version import AlembicVersion
        from models.config import Config
        from models.job import Job
        from models.notifications import Notifications
        from models.system_drives import SystemDrives
        from models.system_info import SystemInfo
        from models.track import Track
        from models.ui_settings import UISettings
        from models.user import User

        _MODEL_REGISTRY = {
            "alembic_version": AlembicVersion,
            "config": Config,
            "job": Job,
            "notifications": Notifications,
            "system_drives": SystemDrives,
            "system_info": SystemInfo,
            "track": Track,
            "ui_settings": UISettings,
            "user": User,
        }
    return _MODEL_REGISTRY


def describe_model(model_name: str) -> dict[str, Any]:
    """
    Describe one model's columns and redaction contract.

    Args:
        model_name: name of a registered model

    Returns:
        dict: model, table, hidden_attribs and column metadata
    """
    registry = _get_registry()
    model = registry.get(str(model_name).lower())
    if model is None:
        raise ValueError(f"Unknown model '{model_name}'. Available: {sorted(registry)}")
    columns = []
    for column in model.__table__.columns:
        columns.append({
            "name": column.name,
            "type": str(column.type),
            "nullable": column.nullable,
            "primary_key": column.primary_key,
        })
    return {
        "model": model.__name__,
        "table": model.__tablename__,
        "hidden_attribs": list(getattr(model, "hidden_attribs", ())),
        "columns": columns,
    }


def query_db(model_name: str, filters: dict[str, Any] | None = None, limit: int = 50) -> dict[str, Any]:
    """
    Query a named model with optional field=value filters.

    Args:
        model_name: name of a registered model
        filters: optional dict of column=value pairs
        limit: max rows to return (default 50, capped at 200)

    Returns:
        dict: model table, row count and serialized rows
    """
    limit = min(limit, 200)
    registry = _get_registry()
    model = registry.get(str(model_name).lower())
    if model is None:
        raise ValueError(f"Unknown model '{model_name}'. Available: {sorted(registry)}")
    valid_columns = {column.name for column in model.__table__.columns}
    query = model.query
    for key, value in (filters or {}).items():
        if key not in valid_columns:
            raise ValueError(f"Unknown column '{key}' on model '{model_name}'")
        query = query.filter_by(**{key: value})
    rows = query.limit(limit).all()
    return {
        "model": model.__tablename__,
        "count": len(rows),
        "rows": [serialize_model(row) for row in rows],
    }


def get_table_counts() -> dict[str, Any]:
    """
    Count rows in every registered table.

    Returns:
        dict: table name to row count
    """
    counts = {}
    for name, model in sorted(_get_registry().items()):
        counts[name] = model.query.count()
    return {"tables": counts}


def get_db_status() -> dict[str, Any]:
    """
    Report the MySQL connection the models run on.

    Returns:
        dict: server version, current database, and per-table storage
        engine and row counts from information_schema
    """
    from models.db_setup import db
    from sqlalchemy import text

    version = db.session.execute(text("SELECT VERSION()")).scalar()
    database = db.session.execute(text("SELECT DATABASE()")).scalar()
    engine_url = db.engine.url
    tables = {}
    rows = db.session.execute(text(
        "SELECT TABLE_NAME, ENGINE, TABLE_ROWS FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE()"
    )).fetchall()
    for table_name, engine_name, table_rows in rows:
        tables[table_name] = {"engine": engine_name, "rows": table_rows}
    return {
        "server_version": version,
        "database": database,
        "host": engine_url.host,
        "port": engine_url.port or 3306,
        "tables": tables,
    }
