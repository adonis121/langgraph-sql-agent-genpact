"""The eval tooling without an LLM: result comparison rules and the reference queries."""
import pytest

from src.db.database import run_query
from src.eval.compare import compare_results, normalized_rows
from src.eval.questions import QUESTIONS


# --- compare_results ---------------------------------------------------------

def test_same_rows_in_another_order_match():
    assert compare_results([(2, "b"), (1, "a")], [(1, "a"), (2, "b")])[0]


def test_columns_in_another_order_and_extra_columns_match():
    agent = [("Maria Garcia", 85.1667, 1), ("Maria Garcia", 75.5, 2)]  # name, avg, id
    assert compare_results(agent, [(1, 85.17), (2, 75.5)])[0]


def test_numbers_are_rounded_and_ints_equal_floats():
    assert compare_results([(57,)], [(57.0,)])[0]
    assert compare_results([(89.004,)], [(89.0,)])[0]
    assert not compare_results([(85.2,)], [(85.17,)])[0]


def test_extra_detail_rows_collapse_to_the_reference_rows():
    agent = [(6, "Lucas Silva", "CS301"), (6, "Lucas Silva", "CS350"), (12, "Ethan Miller", "CS350")]
    assert compare_results(agent, [(6,), (12,)])[0]


def test_missing_or_wrong_rows_fail():
    passed, reason = compare_results([(6,)], [(6,), (12,)])
    assert not passed and "no choice of agent columns" in reason
    assert not compare_results([(6,), (12,), (13,)], [(6,), (12,)])[0]


def test_too_few_columns_fail():
    passed, reason = compare_results([(1,)], [(1, 85.17)])
    assert not passed and "1 columns, the reference needs 2" in reason


def test_empty_reference_needs_an_empty_result():
    assert compare_results([], [])[0]
    assert compare_results([(None,)], [])[0]  # e.g. AVG over no rows
    passed, reason = compare_results([(4,)], [])
    assert not passed and "expected an empty result" in reason
    assert not compare_results([], [(1,)])[0]


# --- reference queries -------------------------------------------------------

def test_question_ids_are_unique_and_there_are_8_to_10():
    ids = [q.id for q in QUESTIONS]
    assert len(set(ids)) == len(ids)
    assert 8 <= len(ids) <= 10


EXPECTED = {
    1: {(i,) for i in (4, 6, 8, 10, 12, 15, 16, 17, 19, 21, 23)},  # 11 students
    2: {(89.0,)},
    3: {("Data Structures", 7), ("Databases", 6), ("Linear Algebra", 6),
        ("Probability Theory", 0), ("Electromagnetism", 6)},
    4: {("Introduction to Programming",)},
    5: {("Fall 2024", 45.0), ("Spring 2025", 79.0), ("Fall 2025", 72.0),
        ("Fall 2025", 68.0), ("Spring 2026", 58.0)},
    7: {(1, 85.17), (2, 75.5)},
    8: set(),
    9: {(6,), (12,)},  # Lucas Silva, Ethan Miller
    10: set(),
}


@pytest.mark.parametrize("item", QUESTIONS, ids=lambda q: f"q{q.id}")
def test_reference_query_gives_the_expected_result(item, university_engine):
    rows = run_query(university_engine, item.sql).rows
    if item.id == 6:
        assert len(rows) == 16  # every failing grade
        return
    assert normalized_rows(rows) == normalized_rows(EXPECTED[item.id])
