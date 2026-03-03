"""Alembic environment — standalone (no Flask)."""
from alembic import context
from sqlalchemy import engine_from_config, pool

import arm.config.config as cfg
from arm.database import db

_SQLALCHEMY_URL = "sqlalchemy.url"

# Alembic Config object
config = context.config

# Set the database URL from ARM config if not already set via command line
if not config.get_main_option(_SQLALCHEMY_URL):
    config.set_main_option(_SQLALCHEMY_URL, "sqlite:///" + cfg.arm_config["DBFILE"])

# Import all models so metadata is populated
import arm.models  # noqa: F401,E402

target_metadata = db.metadata


def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = config.get_main_option(_SQLALCHEMY_URL)
    context.configure(url=url, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
