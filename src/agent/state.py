"""The state that flows through the graph."""
import operator
from typing import Annotated, TypedDict


class AgentState(TypedDict):
    question: str             # the user's original question, never rewritten
    clarification: str | None # the user's reply to the planner's clarifying question
    plan: dict | None         # planner output: {decision, reason, steps, clarifying_question}
    steps: list[str]          # sub-questions from the planner (1-3)
    step_index: int           # the step generate_sql works on; check_result moves it on
    sql: str                  # the latest generated (then validated) query
    error: str | None         # latest failure message, fed back to generate_sql; None when fine
    attempts: int             # generate_sql calls for the current step, reset when the step succeeds
    empty_retry_used: bool    # the one retry for an empty result was used in this step
    last_result: dict | None  # {"columns", "rows"} from execute_sql, waiting for check_result
    # operator.add reducer: nodes return only new entries, LangGraph appends them.
    # Only check_result appends, so this holds accepted results only.
    results: Annotated[list[dict], operator.add]   # {"step_index", "step", "sql", "columns", "rows"}
    answer: str
    status: str               # "running" | "done" | "error" | "rejected" | "needs_clarification"


def initial_state(question: str) -> AgentState:
    return AgentState(
        question=question,
        clarification=None,
        plan=None,
        steps=[],
        step_index=0,
        sql="",
        error=None,
        attempts=0,
        empty_retry_used=False,
        last_result=None,
        results=[],
        answer="",
        status="running",
    )
