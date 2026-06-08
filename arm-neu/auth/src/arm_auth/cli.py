"""CLI for bootstrapping the auth system.

Usage:
    arm-auth init --admin-password <pw> --db-path <path> --users-file <path>
    arm-auth add-user --username <name> --password <pw> --db-path <path> --users-file <path>
"""

import click
import logging

from arm_auth.db import AuthDB
from arm_auth.service import AuthService
from arm_auth.tinyauth.sync import sync_users


def _get_db(db_path: str) -> AuthDB:
    """Create and initialize an AuthDB instance."""
    db = AuthDB()
    db.init_engine(f"sqlite:///{db_path}")
    return db


@click.group()
def main():
    """ARM Auth — manage authentication for the ARM ecosystem."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


@main.command()
@click.option("--db-path", required=True, help="Path to auth SQLite database")
@click.option("--admin-password", required=True, help="Password for the admin user")
@click.option("--users-file", required=True, help="Path to write Tinyauth users file")
def init(db_path: str, admin_password: str, users_file: str):
    """Initialize the auth database with default groups and admin user."""
    db = _get_db(db_path)
    db.create_all()
    svc = AuthService(db)
    svc.seed_defaults()

    try:
        svc.create_user("admin", admin_password, group_name="admin")
        click.echo(f"Initialized auth DB at {db_path} with admin user")
    except ValueError as e:
        if "already exists" in str(e):
            click.echo(f"Admin user already exists — skipping (DB at {db_path})")
        else:
            raise click.ClickException(str(e))

    sync_users(db, users_file)
    db.dispose()


@main.command("add-user")
@click.option("--db-path", required=True, help="Path to auth SQLite database")
@click.option("--username", required=True, help="Username")
@click.option("--password", required=True, help="Password")
@click.option("--group", default="user", help="Group name (default: user)")
@click.option("--users-file", required=True, help="Path to write Tinyauth users file")
def add_user(db_path: str, username: str, password: str, group: str, users_file: str):
    """Add a user to the auth database."""
    db = _get_db(db_path)
    db.create_all()  # ensure tables exist
    svc = AuthService(db)

    try:
        svc.create_user(username, password, group_name=group)
        click.echo(f"Created user '{username}' in group '{group}'")
    except ValueError as e:
        raise click.ClickException(str(e))

    sync_users(db, users_file)
    db.dispose()
