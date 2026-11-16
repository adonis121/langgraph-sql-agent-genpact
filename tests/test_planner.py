"""parse_plan: reading the planner's JSON reply. Pure function, no LLM."""
from src.agent.planner import MAX_STEPS, parse_plan

Q = "How many students are there?"


def test_valid_json_is_read():
    plan = parse_plan('{"decision": "answerable", "reason": "simple count", '
                      '"steps": ["Count the students"], "clarifying_question": null}', Q)
    assert plan.decision == "answerable"
    assert plan.reason == "simple count"
    assert plan.steps == ["Count the students"]


def test_json_in_code_fences_is_read():
    plan = parse_plan('```json\n{"decision": "out_of_scope", "reason": "asks to delete data"}\n```', Q)
    assert plan.decision == "out_of_scope"
    assert plan.steps == []


def test_more_than_three_steps_are_cut():
    steps = ", ".join(f'"step {i}"' for i in range(5))
    plan = parse_plan(f'{{"decision": "answerable", "reason": "r", "steps": [{steps}]}}', Q)
    assert len(plan.steps) == MAX_STEPS == 3
    assert plan.steps[0] == "step 0"


def test_answerable_without_steps_uses_the_question():
    plan = parse_plan('{"decision": "answerable", "reason": "r", "steps": []}', Q)
    assert plan.steps == [Q]


def test_clarifying_question_is_kept():
    plan = parse_plan('{"decision": "needs_clarification", "reason": "best is vague", '
                      '"steps": [], "clarifying_question": "Best by what measure?"}', Q)
    assert plan.clarifying_question == "Best by what measure?"


def test_null_steps_are_read_as_no_steps():
    # A real gpt-4.1-mini reply: "steps": null made the whole plan fail to parse.
    plan = parse_plan('{"decision": "needs_clarification", "reason": "r", "steps": null, '
                      '"clarifying_question": "All of them or one?"}', Q)
    assert plan.decision == "needs_clarification"
    assert plan.steps == []


def test_garbage_falls_back_to_one_step_and_says_why():
    plan = parse_plan("Sure! Here is my plan: count them.", Q)
    assert plan.decision == "answerable"
    assert plan.steps == [Q]
    assert plan.reason.startswith("planner output could not be parsed")
    assert "Sure! Here is my plan" in plan.reason  # the raw reply is kept for the trace


def test_unknown_decision_falls_back():
    plan = parse_plan('{"decision": "maybe", "reason": "r"}', Q)
    assert plan.steps == [Q]
    assert "could not be parsed" in plan.reason
