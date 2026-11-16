"""End-to-end graph runs: scripted fake LLM + the real seeded test database.

One test per path through the graph. Each checks the exact node path, the final status,
and that the fake LLM used all its replies (so no unexpected extra LLM calls).
"""
import json

from langgraph.types import Command

from src.agent import prompts
from src.agent.nodes import MAX_ATTEMPTS
from src.agent.state import initial_state

HAPPY_PATH = ["plan", "generate_sql", "validate_sql", "execute_sql", "check_result"]
BAD_SQL = "SELECT no_such_column FROM students"

BEST_TEACHER_FALL_2025 = """
SELECT t.id, t.name, AVG(e.grade) AS avg_grade FROM enrollments e
JOIN course_offerings o ON o.id = e.offering_id
JOIN teachers t ON t.id = o.teacher_id
JOIN semesters s ON s.id = o.semester_id
WHERE s.name = 'Fall 2025'
GROUP BY t.id ORDER BY avg_grade DESC LIMIT 1"""

FAILED_WITH_TEACHER_3 = """
SELECT st.id, st.name, e.grade FROM enrollments e
JOIN students st ON st.id = e.student_id
JOIN course_offerings o ON o.id = e.offering_id
WHERE o.teacher_id = 3 AND e.grade < 60"""


def plan_json(decision="answerable", steps=None, clarifying_question=None, reason="r"):
    return json.dumps({"decision": decision, "reason": reason, "steps": steps or [],
                       "clarifying_question": clarifying_question})


def run(graph, graph_input, thread="t1"):
    """Stream one graph call. Returns (node path, final state, interrupt value or None)."""
    config = {"configurable": {"thread_id": thread}}
    path, state, question = [], None, None
    for mode, chunk in graph.stream(graph_input, config, stream_mode=["updates", "values"]):
        if mode == "values":
            state = chunk
        elif "__interrupt__" in chunk:
            question = chunk["__interrupt__"][0].value
        else:
            path.extend(chunk)
    return path, state, question


def test_simple_question(make_graph):
    graph, fake = make_graph([
        plan_json(steps=["Count the students"]),
        "SELECT COUNT(*) AS n FROM students",
        "There are 30 students.",
    ])
    path, state, _ = run(graph, initial_state("How many students are there?"))

    assert path == HAPPY_PATH + ["answer"]
    assert state["status"] == "done"
    assert state["answer"] == "There are 30 students."
    assert state["results"][0]["rows"] == [(30,)]
    assert state["results"][0]["sql"].endswith("LIMIT 200")  # validate_sql added it
    assert fake.remaining == 0


def test_multi_step_question_uses_step_1_results_in_step_2(make_graph):
    graph, fake = make_graph([
        plan_json(steps=["Teacher with the highest average grade in Fall 2025",
                         "Students who failed a course taught by the teacher from step 1"]),
        BEST_TEACHER_FALL_2025,
        FAILED_WITH_TEACHER_3,
        "Priya Shah; Lucas Silva and Ethan Miller failed.",
    ])
    path, state, _ = run(graph, initial_state("Best teacher in Fall 2025 and who failed?"))

    assert path == HAPPY_PATH + HAPPY_PATH[1:] + ["answer"]
    assert [r["step_index"] for r in state["results"]] == [0, 1]
    assert state["results"][0]["rows"] == [(3, "Priya Shah", 89.0)]
    assert {row[1] for row in state["results"][1]["rows"]} == {"Lucas Silva", "Ethan Miller"}

    step_2_prompt = fake.prompts[2]
    assert "## Results of earlier steps" in step_2_prompt
    assert "Priya Shah" in step_2_prompt
    assert fake.remaining == 0


def test_sql_error_is_sent_back_and_fixed(make_graph):
    graph, fake = make_graph([
        plan_json(steps=["Count the students"]),
        BAD_SQL,
        "SELECT COUNT(*) FROM students",
        "There are 30 students.",
    ])
    path, state, _ = run(graph, initial_state("How many students are there?"))

    assert path == (["plan", "generate_sql", "validate_sql", "execute_sql"]
                    + HAPPY_PATH[1:] + ["answer"])
    assert "no such column: no_such_column" in fake.prompts[2]  # the retry prompt
    assert BAD_SQL in fake.prompts[2]
    assert state["status"] == "done"
    assert state["attempts"] == 0  # reset when the step was accepted
    assert fake.remaining == 0


def test_empty_result_gets_one_retry_then_is_accepted(make_graph):
    empty_sql = "SELECT id, name FROM students WHERE name = 'Nobody'"
    graph, fake = make_graph([
        plan_json(steps=["Find the student named Nobody"]),
        empty_sql,
        empty_sql,  # the model keeps the filter: the empty result is the true answer
    ])
    path, state, _ = run(graph, initial_state("Find the student named Nobody"))

    assert path == HAPPY_PATH + HAPPY_PATH[1:] + ["answer"]
    assert prompts.EMPTY_RETRY_HINT in fake.prompts[2]
    assert state["results"][0]["rows"] == []
    # No LLM call for the answer: there is nothing to ground it in.
    assert state["answer"] == prompts.EMPTY_ANSWER
    assert state["status"] == "done"
    assert fake.remaining == 0


def test_give_up_after_max_attempts(make_graph):
    graph, fake = make_graph([plan_json(steps=["Count the students"])]
                             + [BAD_SQL] * MAX_ATTEMPTS)
    path, state, _ = run(graph, initial_state("How many students are there?"))

    failing = ["generate_sql", "validate_sql", "execute_sql"]
    assert path == ["plan"] + failing * MAX_ATTEMPTS + ["give_up"]
    assert state["status"] == "error"
    assert state["attempts"] == MAX_ATTEMPTS
    assert state["results"] == []
    assert "no such column" in state["answer"]
    assert fake.remaining == 0


def test_out_of_scope_is_declined_without_sql(make_graph):
    graph, fake = make_graph([
        plan_json(decision="out_of_scope", reason="it asks to delete data"),
    ])
    path, state, _ = run(graph, initial_state("Delete all students who failed a course"))

    assert path == ["plan", "decline"]
    assert state["status"] == "rejected"
    assert "it asks to delete data" in state["answer"]
    assert state["sql"] == ""
    assert len(fake.prompts) == 1  # only the planner was called


def test_clarification_pauses_and_resumes_with_the_reply(make_graph):
    reply = "the highest average grade in Fall 2025"
    graph, fake = make_graph([
        plan_json(decision="needs_clarification", reason="best is vague",
                  clarifying_question="Best by what measure?"),
        plan_json(steps=["Teacher with the highest average grade in Fall 2025"]),
        BEST_TEACHER_FALL_2025,
        "Priya Shah had the highest average grade (89.0).",
    ])
    question = "Who is the best teacher?"

    path, state, asked = run(graph, initial_state(question), thread="clarify")
    assert path == ["plan"]
    assert asked == "Best by what measure?"  # paused by interrupt() in ask_user

    # Resume on the same thread: the checkpointer has the saved state.
    path, state, asked = run(graph, Command(resume=reply), thread="clarify")
    assert asked is None
    assert path == ["ask_user"] + HAPPY_PATH + ["answer"]
    assert reply in fake.prompts[1]  # the second plan call sees the reply
    assert state["question"] == question  # never rewritten
    assert state["clarification"] == reply
    assert state["status"] == "done"
    assert fake.remaining == 0
