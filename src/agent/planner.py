"""The planner's output format and how we read it from the model's plain-text reply.

The model is asked for JSON (see prompts.PLAN_PROMPT) and we validate it here, instead of
using with_structured_output: every node then talks to the LLM the same way
(llm.invoke(prompt).content), and a fake LLM in tests only has to return strings.
"""
from typing import Literal

from pydantic import BaseModel, ValidationError

from src.agent.llm import strip_code_fences

MAX_STEPS = 3
REPLY_IN_REASON = 300  # characters of an unparsable reply kept in the trace

Decision = Literal["answerable", "needs_clarification", "out_of_scope"]


class Plan(BaseModel):
    decision: Decision
    reason: str
    steps: list[str] | None = None  # models often send null when there are no steps
    clarifying_question: str | None = None


def parse_plan(text: str, question: str) -> Plan:
    """Turn the model's reply into a Plan. Never raises.

    If the reply can't be parsed, fall back to answering the question as one step: the SQL
    path still has its own guards (validation, read-only DB), and the reason in the trace
    shows that the planner failed.
    """
    try:
        plan = Plan.model_validate_json(strip_code_fences(text))
    except ValidationError as exc:
        first = exc.errors()[0]["msg"] if exc.errors() else str(exc)
        # Keep the start of the raw reply, so the trace shows what the model actually sent.
        reason = f"planner output could not be parsed: {first}. Reply: {text[:REPLY_IN_REASON]!r}"
        return Plan(decision="answerable", reason=reason, steps=[question])

    steps = [s.strip() for s in plan.steps or [] if s.strip()][:MAX_STEPS]
    if plan.decision == "answerable" and not steps:
        steps = [question]
    return plan.model_copy(update={"steps": steps})

