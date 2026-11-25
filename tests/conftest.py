"""The database fixture. Database tests skip when TEST_DATABASE_URL isn't set.

The schema comes from the Alembic migration, so the migration is what the tests exercise.
TEST_DATABASE_URL must point at a database the tests may wipe: its public schema is dropped.
"""

from __future__ import annotations

from pathlib import Path

import alembic.command
import alembic.config
import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from storage.config import load_test_database_url
from storage.db import make_engine

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def db_engine():
    url = load_test_database_url()
    if not url:
        pytest.skip("TEST_DATABASE_URL isn't set")
    engine = make_engine(url)
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public"))
    config = alembic.config.Config(str(ROOT / "alembic.ini"))
    config.attributes["database_url"] = url
    alembic.command.upgrade(config, "head")
    yield engine
    engine.dispose()


@pytest.fixture
def db(db_engine):
    """A session inside a transaction that's rolled back after the test."""
    connection = db_engine.connect()
    outer = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    yield session
    session.close()
    outer.rollback()
    connection.close()
