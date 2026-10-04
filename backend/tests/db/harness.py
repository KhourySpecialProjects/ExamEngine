"""
Real-Postgres test database for integration tests.

The tests share the dev stack's Postgres server but use their own database
(default ``exam_engine_test``), never the one ``DATABASE_URL`` points at.
Two hard checks keep them away from real data:

* the configured URL must name a database ending in ``_test`` that is not the
  app's database (``check_test_database_url``);
* the live connection must report a ``current_database()`` ending in ``_test``
  before the schema is dropped and rebuilt (``reset_schema``).
"""

import os
import re

from sqlalchemy import URL, Engine, create_engine, make_url, text


DEFAULT_TEST_DATABASE_URL = (
    "postgresql+psycopg2://postgres:postgres@localhost:5434/exam_engine_test"
)
TEST_DATABASE_SUFFIX = "_test"
_SAFE_NAME = re.compile(r"[a-z0-9_]+_test")


class UnsafeTestDatabaseError(RuntimeError):
    """The configured test database could hold real data; refuse to use it."""


def _checked_name(url: URL) -> str:
    """The URL's database name, if it is a safe ``_test`` name; else raise."""
    name = url.database or ""
    if not _SAFE_NAME.fullmatch(name):
        raise UnsafeTestDatabaseError(
            f"Test database name {name!r} must end in {TEST_DATABASE_SUFFIX!r} "
            "and use only lowercase letters, digits and underscores. "
            "Set TEST_DATABASE_URL to a dedicated test database."
        )
    return name


def check_test_database_url(url: str, app_database_url: str | None) -> URL:
    """
    Return the parsed test URL, or raise if it doesn't name a test database.

    The name must be lowercase letters, digits and underscores ending in
    ``_test``, and must differ from the app's database name.
    """
    parsed = make_url(url)
    name = _checked_name(parsed)
    if app_database_url is not None and make_url(app_database_url).database == name:
        raise UnsafeTestDatabaseError(
            f"Test database {name!r} is the app's database (DATABASE_URL). "
            "Set TEST_DATABASE_URL to a dedicated test database."
        )
    return parsed


def configured_test_database_url(app_database_url: str | None) -> URL:
    """The checked test URL from ``TEST_DATABASE_URL`` or the default."""
    url = os.environ.get("TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL)
    return check_test_database_url(url, app_database_url)


def ensure_database(url: URL) -> None:
    """Create the test database on its server if it doesn't exist yet."""
    name = _checked_name(url)
    server = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with server.connect() as connection:
            exists = connection.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": name},
            ).scalar()
            if not exists:
                # Name is validated above: lowercase letters, digits, underscores.
                connection.execute(text(f'CREATE DATABASE "{name}"'))
    finally:
        server.dispose()


def reset_schema(engine: Engine) -> None:
    """
    Drop and rebuild the test database's tables from the current models.

    Uses the app's ``init_db`` so the schema matches startup exactly. Refuses
    to run unless the connected database's name ends in ``_test``.
    """
    from src.core.database import init_db

    with engine.begin() as connection:
        current = connection.execute(text("SELECT current_database()")).scalar()
        if not current or not current.endswith(TEST_DATABASE_SUFFIX):
            raise UnsafeTestDatabaseError(
                f"Refusing to reset {current!r}: not a {TEST_DATABASE_SUFFIX!r} "
                "database."
            )
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    init_db(engine)
