"""Graph nodes. Each takes the state (plus bound dependencies) and returns only the keys it changes."""
import re

from sqlalchemy import Engine

from src.agent import prompts
from src.agent.state import AgentState
from src.db.database import run_query


def generate_sql(state: AgentState, *, llm, schema: str, notes: str, dialect: str) -> dict:
    prompt = prompts.GENERATE_SQL_PROMPT.format(
        dialect=dialect,
        schema=schema,
        notes=notes,
        question=state["steps"][state["step_index"]],
    )
    reply = llm.invoke(prompt)
    return {"sql": extract_sql(reply.content)}


def execute_sql(state: AgentState, *, engine: Engine) -> dict:
    try:
        result = run_query(engine, state["sql"])
    except Exception as exc:  # any DB error is reported back, not raised
        return {"error": str(exc), "status": "error"}

    entry = {
        "step": state["steps"][state["step_index"]],
        "sql": state["sql"],
        "columns": result.columns,
        "rows": result.rows,
    }
    return {"results": [entry], "error": None}


def answer(state: AgentState, *, llm, notes: str) -> dict:
    # Without real rows there is nothing to ground an answer in, so skip the LLM.
    if state["error"]:
        return {"answer": prompts.ERROR_ANSWER.format(error=state["error"]), "status": "error"}

    last = state["results"][-1]
    if not last["rows"]:
        return {"answer": prompts.EMPTY_ANSWER, "status": "done"}

    prompt = prompts.ANSWER_PROMPT.format(
        notes=notes,
        question=state["question"],
        sql=last["sql"],
        table=prompts.format_rows_as_table(last["columns"], last["rows"]),
    )
    reply = llm.invoke(prompt)
    return {"answer": reply.content.strip(), "status": "done"}


def extract_sql(text: str) -> str:
    """Strip markdown code fences the model sometimes wraps around the query."""
    match = re.search(r"```(?:\w+)?\s*(.*?)```", text, re.DOTALL)
    return (match.group(1) if match else text).strip()
