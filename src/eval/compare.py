"""Compare the agent's query result to a reference result. Pure functions, no LLM, no DB.

We compare RESULTS, not SQL text: two different queries can both be right.
- Values: numbers rounded to 2 decimals (57 == 57.0, 85.1666 == 85.17), strings stripped.
- Columns: names and order are ignored, extra agent columns are allowed. The reference
  returns only the columns that define a correct answer; we try every way to pick agent
  columns for them and pass if any choice gives the reference rows.
- Rows: order is ignored and rows are compared as sets (after picking columns), because
  extra agent columns can change granularity (one row per failure vs one per student).
- Empty reference: the agent result must be empty too (no rows, or one all-NULL row).
"""
import numbers
from itertools import permutations

from src.agent.nodes import is_empty_result

DECIMALS = 2


def normalize(value):
    if isinstance(value, numbers.Number) and not isinstance(value, bool):
        return round(float(value), DECIMALS)
    if isinstance(value, str):
        return value.strip()
    return value


def normalized_rows(rows) -> set[tuple]:
    return {tuple(normalize(v) for v in row) for row in rows}


def compare_results(agent_rows: list[tuple], reference_rows: list[tuple]) -> tuple[bool, str]:
    """Return (passed, reason). The reason says what differs when it fails."""
    if is_empty_result(reference_rows):
        if is_empty_result(agent_rows):
            return True, "both empty"
        return False, f"expected an empty result, got {len(agent_rows)} rows"
    if is_empty_result(agent_rows):
        return False, f"agent result is empty, expected {len(reference_rows)} rows"

    expected = normalized_rows(reference_rows)
    agent_width, needed = len(agent_rows[0]), len(reference_rows[0])
    if agent_width < needed:
        return False, f"agent result has {agent_width} columns, the reference needs {needed}"

    agent = [tuple(normalize(v) for v in row) for row in agent_rows]
    for columns in permutations(range(agent_width), needed):
        if {tuple(row[i] for i in columns) for row in agent} == expected:
            return True, "match"
    return False, (f"no choice of agent columns gives the reference rows "
                   f"(agent: {len(agent_rows)} rows x {agent_width} columns, "
                   f"reference: {len(expected)} distinct rows x {needed} columns)")
