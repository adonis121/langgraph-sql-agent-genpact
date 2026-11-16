"""Routing functions of the graph: plain functions of the state, no LLM."""
from src.agent.graph import after_check, after_plan
from src.agent.nodes import MAX_ATTEMPTS, check_result, decline
from src.agent.state import initial_state


def state_with(**changes):
    return {**initial_state("Q"), **changes}


def plan(decision, reason="r"):
    return {"decision": decision, "reason": reason, "steps": [], "clarifying_question": None}


def test_answerable_goes_to_sql():
    assert after_plan(state_with(plan=plan("answerable"))) == "generate_sql"


def test_out_of_scope_is_declined_without_sql():
    assert after_plan(state_with(plan=plan("out_of_scope"))) == "decline"


def test_vague_question_asks_the_user_once():
    assert after_plan(state_with(plan=plan("needs_clarification"))) == "ask_user"
    still_vague = state_with(plan=plan("needs_clarification"), clarification="the nicest one")
    assert after_plan(still_vague) == "decline"
    # An empty reply still counts as asked, so the graph can't loop asking forever.
    assert after_plan(state_with(plan=plan("needs_clarification"), clarification="")) == "decline"


def test_after_an_accepted_step_go_to_the_next_step_then_answer():
    two_steps = ["step 1", "step 2"]
    assert after_check(state_with(steps=two_steps, step_index=1)) == "generate_sql"
    assert after_check(state_with(steps=two_steps, step_index=2)) == "answer"


def test_after_check_with_an_error_retries_or_gives_up():
    assert after_check(state_with(steps=["s"], error="Empty result", attempts=1)) == "generate_sql"
    assert after_check(state_with(steps=["s"], error="x", attempts=MAX_ATTEMPTS)) == "give_up"


def test_check_result_accepts_and_moves_to_the_next_step():
    state = state_with(steps=["s1", "s2"], step_index=0, sql="SELECT 1", attempts=1,
                       last_result={"columns": ["n"], "rows": [(1,)]})
    changes = check_result(state)
    assert changes["step_index"] == 1
    assert changes["results"][0]["step"] == "s1"
    assert changes["attempts"] == 0


def test_decline_messages():
    rejected = decline(state_with(plan=plan("out_of_scope", "it asks to delete data")))
    assert rejected["status"] == "rejected"
    assert "it asks to delete data" in rejected["answer"]

    unclear = decline(state_with(plan=plan("needs_clarification", "no measure given")))
    assert unclear["status"] == "needs_clarification"
