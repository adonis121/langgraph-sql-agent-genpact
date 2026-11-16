"""Graph nodes. Each takes the state (plus bound dependencies) and returns only the keys it changes."""
import textwrap

from langgraph.types import interrupt
from sqlalchemy import Engine

from src.agent import prompts
from src.agent.llm import strip_code_fences
from src.agent.planner import parse_plan
from src.agent.sql_validation import validate_sql as check_sql_rules
from src.agent.state import AgentState
from src.db.database import run_query

MAX_ATTEMPTS = 3  # generate_sql calls per step before give_up


def plan(state: AgentState, *, llm, schema: str, notes: str) -> dict:
    clarification = state["clarification"]
    prompt = prompts.PLAN_PROMPT.format(
        schema=schema,
        notes=notes,
        question=state["question"],
        clarification=(prompts.CLARIFICATION_SECTION.format(clarification=clarification)
                       if clarification else ""),
        clarification_rule=(prompts.CLARIFICATION_GIVEN_RULE
                            if clarification is not None else ""),
    )
    result = parse_plan(llm.invoke(prompt).content, state["question"])
    return {"plan": result.model_dump(), "steps": result.steps}


def ask_user(state: AgentState) -> dict:
    # No LLM call here on purpose: on resume LangGraph re-runs this node from the top,
    # and interrupt() then returns the user's reply instead of pausing again.
    reply = interrupt(state["plan"]["clarifying_question"] or state["plan"]["reason"])
    return {"clarification": str(reply).strip()}


def decline(state: AgentState) -> dict:
    """End without running SQL: out of scope, or still unclear after one clarification."""
    reason = state["plan"]["reason"]
    if state["plan"]["decision"] == "out_of_scope":
        return {"answer": prompts.OUT_OF_SCOPE_ANSWER.format(reason=reason), "status": "rejected"}
    return {"answer": prompts.STILL_UNCLEAR_ANSWER.format(reason=reason),
            "status": "needs_clarification"}


def generate_sql(state: AgentState, *, llm, schema: str, notes: str, dialect: str) -> dict:
    previous = ""
    if state["results"]:  # later steps see what earlier steps found
        previous = prompts.PREVIOUS_STEPS_SECTION.format(
            steps=prompts.format_step_results(state["results"]))

    retry = ""
    if state["error"]:  # the previous attempt failed: show the model its SQL and the error
        retry = prompts.RETRY_SECTION.format(sql=state["sql"], error=state["error"])

    prompt = prompts.GENERATE_SQL_PROMPT.format(
        dialect=dialect,
        schema=schema,
        notes=notes,
        previous_steps=previous,
        question=state["steps"][state["step_index"]],
        retry=retry,
    )
    reply = llm.invoke(prompt)
    return {"sql": strip_code_fences(reply.content), "attempts": state["attempts"] + 1}


def validate_sql(state: AgentState) -> dict:
    try:
        sql = check_sql_rules(state["sql"])
    except ValueError as exc:
        return {"error": f"Validation failed: {exc}"}
    return {"sql": sql, "error": None}


def execute_sql(state: AgentState, *, engine: Engine) -> dict:
    try:
        result = run_query(engine, state["sql"])
    except Exception as exc:  # any DB error goes back to the model, not raised
        # exc.orig is the driver's short message ("no such column: x"), without
        # SQLAlchemy's wrapper text and link.
        return {"error": f"Database error: {getattr(exc, 'orig', exc)}"}
    return {"last_result": {"columns": result.columns, "rows": result.rows}, "error": None}


def check_result(state: AgentState) -> dict:
    rows = state["last_result"]["rows"]
    can_retry = not state["empty_retry_used"] and state["attempts"] < MAX_ATTEMPTS
    if is_empty_result(rows) and can_retry:
        return {"error": prompts.EMPTY_RETRY_HINT, "empty_retry_used": True}

    # Accepted, including a second empty result: "no records" can be the true answer.
    entry = {
        "step_index": state["step_index"],
        "step": state["steps"][state["step_index"]],
        "sql": state["sql"],
        **state["last_result"],
    }
    return {
        "results": [entry],
        "step_index": state["step_index"] + 1,
        "last_result": None,
        "error": None,
        "attempts": 0,
        "empty_retry_used": False,
    }


def answer(state: AgentState, *, llm, notes: str) -> dict:
    results = state["results"]
    if all(is_empty_result(r["rows"]) for r in results):  # nothing to ground an answer in
        return {"answer": prompts.EMPTY_ANSWER, "status": "done"}

    clarification = state["clarification"]
    prompt = prompts.ANSWER_PROMPT.format(
        notes=notes,
        question=state["question"],
        clarification=(prompts.CLARIFICATION_SECTION.format(clarification=clarification)
                       if clarification else ""),
        steps=prompts.format_step_results(results),
    )
    reply = llm.invoke(prompt)
    return {"answer": reply.content.strip(), "status": "done"}


def give_up(state: AgentState) -> dict:
    message = prompts.GIVE_UP_ANSWER.format(
        attempts=state["attempts"],
        sql=textwrap.indent(state["sql"] or "(none)", "  "),
        error=state["error"],
    )
    return {"answer": message, "status": "error"}


def is_empty_result(rows: list[tuple]) -> bool:
    """No rows, or one row of only NULLs (e.g. AVG over nothing). COUNT = 0 is a real answer."""
    if not rows:
        return True
    return len(rows) == 1 and all(value is None for value in rows[0])

