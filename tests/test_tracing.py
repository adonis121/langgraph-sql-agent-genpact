"""Tracing without an LLM: row truncation, the trace file format, and the timeline printer."""
import json
import uuid

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
    assert graph.config["metadata"] == {"question": "Q", "run_id": run_id, "model": "m"}


def test_format_trace_shows_sql_error_and_answer(tmp_path):
    writer = TraceWriter(str(uuid.uuid4()), tmp_path)
    writer.start("Q", "m")
    writer.node("execute_sql", {"error": "Database error: no such column: x"}, 2.0)
    writer.end({"status": "error", "answer": "Sorry."}, 2.0)

    text = format_trace(load_trace(writer.path))
    assert "[1] execute_sql" in text
    assert "ERROR: Database error: no such column: x" in text
    assert "status=error" in text and "Sorry." in text


def test_trace_lines_are_valid_json_even_with_non_json_values(tmp_path):
    from datetime import date
    writer = TraceWriter(str(uuid.uuid4()), tmp_path)
    writer.node("execute_sql", {"last_result": {"columns": ["d"], "rows": [(date(2024, 9, 1),)]}}, 1.0)
    line = json.loads(writer.path.read_text())
    assert line["changes"]["last_result"]["rows"] == [["2024-09-01"]]
