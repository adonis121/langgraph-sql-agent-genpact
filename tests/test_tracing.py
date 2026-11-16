"""Tracing without an LLM: row truncation, the trace file format, and the timeline printer."""
import json
import uuid

import pytest
from langgraph.types import Command, Interrupt

from src.show_trace import format_trace, load_trace
from src.tracing import MAX_TRACE_ROWS, TraceWriter, compact, run_traced


def test_compact_cuts_big_results_and_keeps_the_total():
    rows = [(i,) for i in range(MAX_TRACE_ROWS + 5)]
    out = compact({"last_result": {"columns": ["n"], "rows": rows}})

    assert len(out["last_result"]["rows"]) == MAX_TRACE_ROWS
    assert out["last_result"]["row_count"] == MAX_TRACE_ROWS + 5
    assert out["last_result"]["truncated"] is True


def test_compact_keeps_small_results_and_other_keys():
    changes = {"sql": "SELECT 1", "results": [{"columns": ["n"], "rows": [(1,)]}]}
    out = compact(changes)

    assert out["sql"] == "SELECT 1"
    assert out["results"][0]["rows"] == [(1,)]
    assert out["results"][0]["row_count"] == 1
    assert "truncated" not in out["results"][0]


def test_trace_file_has_start_nodes_end_in_order(tmp_path):
    run_id = str(uuid.uuid4())
    writer = TraceWriter(run_id, tmp_path)
    writer.start("How many students?", "fake-model")
    writer.node("generate_sql", {"sql": "SELECT COUNT(*) FROM s", "attempts": 1}, 5.0)
    writer.node("execute_sql", {"last_result": {"columns": ["n"], "rows": [(12,)]}}, 1.0)
    writer.end({"status": "done", "answer": "12 students."}, 6.0)

    records = load_trace(writer.path)
    assert writer.path.name == f"{run_id}.jsonl"
    assert [r["event"] for r in records] == ["start", "node", "node", "end"]
    assert all(r["run_id"] == run_id for r in records)
    assert records[0]["question"] == "How many students?"
    assert records[1]["changes"]["sql"] == "SELECT COUNT(*) FROM s"
    assert records[-1]["answer"] == "12 students."


class FakeStreamingGraph:
    """Stands in for a compiled graph: replays fixed stream chunks, records the config."""

    def __init__(self, chunks):
        self.chunks = chunks
        self.config = None

    def stream(self, state, config, stream_mode):
        self.config = config
        yield from self.chunks


def test_run_traced_writes_each_update_and_returns_the_final_state(tmp_path):
    final = {"question": "Q", "status": "done", "answer": "A"}
    graph = FakeStreamingGraph([
        ("values", {"question": "Q"}),
        ("updates", {"generate_sql": {"sql": "SELECT 1", "attempts": 1}}),
        ("updates", {"answer": {"answer": "A", "status": "done"}}),
        ("values", final),
    ])

    state, run_id, path = run_traced(graph, {"question": "Q"}, model="m", trace_dir=tmp_path)

    assert state == final
    nodes = [r["node"] for r in load_trace(path) if r["event"] == "node"]
    assert nodes == ["generate_sql", "answer"]
    # LangSmith gets the same id as the file, plus a name, tags and metadata.
    assert str(graph.config["run_id"]) == run_id
    assert graph.config["metadata"] == {"question": "Q", "run_id": run_id, "model": "m",
                                        "thread_id": run_id}
    # The checkpointer keys the saved state by thread_id.
    assert graph.config["configurable"] == {"thread_id": run_id}


class FakePausingGraph:
    """First call pauses with an interrupt, the second (the resume) finishes."""

    def __init__(self):
        self.calls = []  # (input, config) per stream call

    def stream(self, graph_input, config, stream_mode):
        self.calls.append((graph_input, config))
        if len(self.calls) == 1:
            yield ("updates", {"plan": {"plan": {"decision": "needs_clarification"}}})
            yield ("updates", {"__interrupt__": (Interrupt(value="Best by what measure?"),)})
        else:
            yield ("updates", {"ask_user": {"clarification": "highest average grade"}})
            yield ("updates", {"answer": {"answer": "A", "status": "done"}})
            yield ("values", {"question": "Q", "status": "done", "answer": "A"})


def test_run_traced_asks_the_user_and_resumes_on_the_same_thread(tmp_path):
    graph = FakePausingGraph()
    asked = []

    def ask_user(question):
        asked.append(question)
        return "highest average grade"

    state, run_id, path = run_traced(graph, {"question": "Q"}, model="m",
                                     ask_user=ask_user, trace_dir=tmp_path)

    assert asked == ["Best by what measure?"]
    assert state["answer"] == "A"
    resume_input, resume_config = graph.calls[1]
    assert isinstance(resume_input, Command) and resume_input.resume == "highest average grade"
    assert resume_config["configurable"] == {"thread_id": run_id}
    assert str(resume_config["run_id"]) != run_id  # a new LangSmith run in the same thread

    records = load_trace(path)
    assert [r["event"] for r in records] == [
        "start", "node", "interrupt", "resume", "node", "node", "end"]
    assert records[2]["question"] == "Best by what measure?"
    assert records[3]["reply"] == "highest average grade"


def test_run_traced_without_ask_user_fails_clearly_on_an_interrupt(tmp_path):
    with pytest.raises(RuntimeError, match="no ask_user"):
        run_traced(FakePausingGraph(), {"question": "Q"}, model="m", trace_dir=tmp_path)


def test_format_trace_shows_sql_error_and_answer(tmp_path):
    writer = TraceWriter(str(uuid.uuid4()), tmp_path)
    writer.start("Q", "m")
    writer.node("execute_sql", {"error": "Database error: no such column: x"}, 2.0)
    writer.end({"status": "error", "answer": "Sorry."}, 2.0)

    text = format_trace(load_trace(writer.path))
    assert "[1] execute_sql" in text
    assert "ERROR: Database error: no such column: x" in text
    assert "status=error" in text and "Sorry." in text


def test_format_trace_shows_plan_and_clarification(tmp_path):
    writer = TraceWriter(str(uuid.uuid4()), tmp_path)
    writer.start("Who is the best teacher?", "m")
    writer.node("plan", {"plan": {"decision": "needs_clarification", "reason": "best is vague",
                                  "steps": [], "clarifying_question": "Best by what?"}}, 1.0)
    writer.interrupt("Best by what?")
    writer.resume("highest average grade")
    writer.node("plan", {"plan": {"decision": "answerable", "reason": "clear now",
                                  "steps": ["Teacher with the highest average grade"],
                                  "clarifying_question": None}}, 1.0)

    text = format_trace(load_trace(writer.path))
    assert "decision=needs_clarification" in text
    assert "paused, asked the user: Best by what?" in text
    assert "user replied: highest average grade" in text
    assert "step 1: Teacher with the highest average grade" in text


def test_trace_lines_are_valid_json_even_with_non_json_values(tmp_path):
    from datetime import date
    writer = TraceWriter(str(uuid.uuid4()), tmp_path)
    writer.node("execute_sql", {"last_result": {"columns": ["d"], "rows": [(date(2024, 9, 1),)]}}, 1.0)
    line = json.loads(writer.path.read_text())
    assert line["changes"]["last_result"]["rows"] == [["2024-09-01"]]
