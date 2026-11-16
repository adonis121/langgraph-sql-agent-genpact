"""The state that flows through the graph."""
import operator
from typing import Annotated, TypedDict


class AgentState(TypedDict):
    question: str
    steps: list[str]          # sub-questions; for now just [question], the planner fills it later
    step_index: int           # which step generate_sql is working on
    sql: str                  # the latest generated query
    error: str | None         # latest failure message, None when fine
    attempts: int             # tries for the current step (used once retries exist)
    # operator.add reducer: nodes return only new entries, LangGraph appends them.
    results: Annotated[list[dict], operator.add]   # {"step", "sql", "columns", "rows"}
    answer: str
    status: str               # "running" | "done" | "error"


def initial_state(question: str) -> AgentState:
    return AgentState(
        question=question,
        steps=[question],
        step_index=0,
        sql="",
        error=None,
        attempts=0,
        results=[],
        answer="",
        status="running",
    )
