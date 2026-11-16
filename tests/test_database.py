"""Tests for the read-only DB layer (src/db/database.py). No LLM."""
import pytest
from sqlalchemy.exc import OperationalError

from src.db.build_db import build_database
from src.db.database import connect_readonly, run_query, schema_as_text


@pytest.fixture(scope="module")
def db_path(tmp_path_factory):
    path = tmp_path_factory.mktemp("db") / "university.db"
    build_database(path)
    return path


@pytest.fixture(scope="module")
def engine(db_path):
    engine = connect_readonly(db_path)
    yield engine
    engine.dispose()


def test_missing_file_fails_fast(tmp_path):
    with pytest.raises(FileNotFoundError):
        connect_readonly(tmp_path / "nope.db")


def test_writes_are_rejected(engine):
    with pytest.raises(OperationalError):
        run_query(engine, "INSERT INTO departments (name) VALUES ('Hacking')")
    assert run_query(engine, "SELECT COUNT(*) FROM departments").rows == [(3,)]


def test_query_only_pragma_is_on(engine):
    assert run_query(engine, "PRAGMA query_only").rows == [(1,)]


def test_schema_text_lists_every_table_and_foreign_keys(engine):
    text = schema_as_text(engine)
    tables = [row[0] for row in run_query(
        engine, "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).rows]
    assert len(tables) == 7
    for table in tables:
        assert f"Table {table}" in text
    assert "student_id INTEGER NOT NULL -> students.id" in text
    assert "grade REAL NULL" in text


def test_run_query_returns_columns_and_rows(engine):
    result = run_query(engine, "SELECT id, name FROM departments ORDER BY id")
    assert result.columns == ["id", "name"]
    assert len(result.rows) == 3
    assert all(isinstance(row, tuple) for row in result.rows)
