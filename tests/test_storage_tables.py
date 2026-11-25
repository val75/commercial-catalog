from __future__ import annotations

import pytest
from sqlalchemy import inspect, select

from storage.config import StorageConfigError, load_database_url
from storage.tables import Document, Draft


def test_database_url_comes_from_the_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://example/db")
    assert load_database_url(tmp_path / "missing.env") == "postgresql+psycopg://example/db"


def test_database_url_falls_back_to_the_env_file(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    (tmp_path / ".env").write_text("DATABASE_URL=postgresql+psycopg://from-file/db\n")
    assert load_database_url(tmp_path / ".env") == "postgresql+psycopg://from-file/db"


def test_a_missing_database_url_says_which_setting(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(StorageConfigError, match="DATABASE_URL"):
        load_database_url(tmp_path / "missing.env")


def test_the_migration_creates_the_five_tables(db):
    names = set(inspect(db.get_bind()).get_table_names())
    assert {"documents", "imports", "drafts", "reviews", "approved_quotes"} <= names


def test_a_draft_keeps_its_json_exactly(db):
    document = Document(
        sha256="ab" * 32,
        source_type="pdf",
        source_name="Q-1.pdf",
        original_path="x",
        markdown="# Q-1",
        warnings=[],
        meta={},
    )
    db.add(document)
    db.flush()
    db.add(Draft(document_id=document.id, position=0, draft={"quote_number": "Q-1", "items": []}, checks={}))
    db.flush()
    assert db.scalars(select(Draft)).one().draft == {"quote_number": "Q-1", "items": []}
