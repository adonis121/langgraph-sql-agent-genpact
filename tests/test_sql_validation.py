"""Tests for validate_sql (one per rule) and is_empty_result. No LLM, no database."""
import pytest

from src.agent.nodes import is_empty_result
from src.agent.sql_validation import WRITE_KEYWORDS, validate_sql


# --- Rule: only SELECT or WITH ----------------------------------------------

def test_accepts_select():
    assert validate_sql("SELECT name FROM students").startswith("SELECT name FROM students")


def test_accepts_with():
    sql = "WITH s AS (SELECT id FROM students) SELECT COUNT(*) FROM s"
    assert validate_sql(sql).startswith(sql)


def test_rejects_non_select():
    with pytest.raises(ValueError, match="Only SELECT or WITH"):
        validate_sql("PRAGMA table_info(students)")


def test_rejects_empty_sql():
    with pytest.raises(ValueError, match="empty"):
        validate_sql("   ;  ")


# --- Rule: a single statement -----------------------------------------------

def test_rejects_multiple_statements():
    with pytest.raises(ValueError, match="one statement"):
        validate_sql("SELECT 1; SELECT 2")


def test_allows_one_trailing_semicolon():
    assert validate_sql("SELECT 1;") == "SELECT 1\nLIMIT 200"


# --- Rule: no write keywords ------------------------------------------------

@pytest.mark.parametrize("keyword", WRITE_KEYWORDS)
def test_rejects_write_keyword(keyword):
    with pytest.raises(ValueError, match=f"Write keyword not allowed: {keyword}"):
        validate_sql(f"WITH x AS (SELECT 1) {keyword.lower()} something")


def test_allows_keywords_in_strings_and_names():
    sql = "SELECT created_at FROM enrollments WHERE status = 'DROPPED' -- delete later"
    assert validate_sql(sql).startswith(sql)


# --- Rule: add a LIMIT if missing -------------------------------------------

def test_adds_limit_when_missing():
    assert validate_sql("SELECT name FROM students") == "SELECT name FROM students\nLIMIT 200"


def test_limit_goes_after_a_trailing_comment():
    # On a new line, so the comment does not swallow the LIMIT.
    assert validate_sql("SELECT 1 -- one", row_limit=5) == "SELECT 1 -- one\nLIMIT 5"


def test_keeps_existing_limit():
    assert validate_sql("SELECT name FROM students LIMIT 3") == "SELECT name FROM students LIMIT 3"


# --- is_empty_result: decides the empty-result retry ------------------------

@pytest.mark.parametrize("rows, expected", [
    ([], True),                 # no rows
    ([(None,)], True),          # AVG over no grades
    ([(None, None)], True),     # all-NULL row with several columns
    ([(0,)], False),            # COUNT = 0 is a real answer
    ([(None,), (None,)], False),  # several rows are real data, even if NULL
])
def test_is_empty_result(rows, expected):
    assert is_empty_result(rows) is expected
