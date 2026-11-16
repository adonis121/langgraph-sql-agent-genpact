"""Run the graph with tracing: LangSmith (if configured) plus a local traces/<run_id>.jsonl.

The nodes know nothing about this module. We stream the graph and write one JSON line per
node from the state changes it returned, so the file shows the full path:
question -> nodes -> SQL -> DB rows -> answer.
If the graph pauses to ask the user (interrupt), the question and the reply are written too,
and the resumed run appends to the same file.
"""
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from langgraph.types import Command

TRACE_DIR = Path(__file__).resolve().parents[1] / "traces"
MAX_TRACE_ROWS = 20  # keep trace files small; the total row count is still recorded
RUN_NAME = "sql-qa-agent"
TAGS = ["sql-agent"]


class TraceWriter:
    """Appends one JSON line per event to traces/<run_id>.jsonl, flushed immediately,
    so a crash mid-run still leaves a partial trace."""

    def __init__(self, run_id: str, trace_dir: Path = TRACE_DIR):
        self.run_id = run_id
        self.path = Path(trace_dir) / f"{run_id}.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def start(self, question: str, model: str | None) -> None:
        self._write({"event": "start", "question": question, "model": model})

    def node(self, name: str, changes: dict, duration_ms: float) -> None:
        self._write({
            "event": "node",
            "node": name,
            "duration_ms": round(duration_ms, 1),
            "changes": compact(changes),
        })

    def interrupt(self, question: str) -> None:
        self._write({"event": "interrupt", "question": question})

    def resume(self, reply: str) -> None:
        self._write({"event": "resume", "reply": reply})

    def end(self, state: dict, total_ms: float) -> None:
        self._write({
            "event": "end",
            "status": state.get("status"),
            "answer": state.get("answer"),
            "total_ms": round(total_ms, 1),
        })

    def _write(self, record: dict) -> None:
        line = {"run_id": self.run_id, "ts": datetime.now(timezone.utc).isoformat(), **record}
        with self.path.open("a") as f:
            # default=str: DB values like dates or Decimals become strings instead of failing.
            f.write(json.dumps(line, default=str) + "\n")


def compact(changes: dict | None) -> dict:
    """Copy of a node's changes with every rows list cut to MAX_TRACE_ROWS."""
    changes = dict(changes or {})
    if changes.get("last_result"):
        changes["last_result"] = _cut_rows(changes["last_result"])
    if changes.get("results"):
        changes["results"] = [_cut_rows(entry) for entry in changes["results"]]
    return changes


def _cut_rows(result: dict) -> dict:
    rows = result.get("rows") or []
    cut = {**result, "rows": rows[:MAX_TRACE_ROWS], "row_count": len(rows)}
    if len(rows) > MAX_TRACE_ROWS:
        cut["truncated"] = True
    return cut


def langsmith_config(run_id: str, question: str, model: str | None, thread_id: str) -> dict:
    """LangChain reads this config; without LangSmith env vars it is simply unused.

    thread_id is also the checkpointer's key, so a resumed run continues the same state.
    """
    return {
        "run_id": uuid.UUID(run_id),  # first call: same id as the local file, easy to match
        "run_name": RUN_NAME,
        "tags": TAGS,
        "metadata": {"question": question, "run_id": thread_id, "model": model,
                     "thread_id": thread_id},  # LangSmith groups runs of one thread
        "configurable": {"thread_id": thread_id},
    }


def run_traced(graph, state: dict, *, model: str | None,
               ask_user: Callable[[str], str] | None = None, trace_dir: Path = TRACE_DIR):
    """Run the graph, trace each node, return (final_state, run_id, trace_path).

    ask_user(question) -> reply is called when the graph pauses with interrupt().
    """
    run_id = str(uuid.uuid4())
    writer = TraceWriter(run_id, trace_dir)
    writer.start(state["question"], model)

    started = time.perf_counter()
    graph_input, call_id, final_state = state, run_id, state
    while True:
        config = langsmith_config(call_id, state["question"], model, thread_id=run_id)
        final_state, question = _stream(graph, graph_input, config, writer, final_state)
        if question is None:
            break
        if ask_user is None:
            raise RuntimeError(f"The graph asked a question but no ask_user was given: {question}")
        writer.interrupt(question)
        reply = ask_user(question)
        writer.resume(reply)
        # Each graph call is its own LangSmith run; the thread_id ties them together.
        graph_input, call_id = Command(resume=reply), str(uuid.uuid4())

    writer.end(final_state, (time.perf_counter() - started) * 1000)
    return final_state, run_id, writer.path


def _stream(graph, graph_input, config: dict, writer: TraceWriter, final_state: dict):
    """Stream one graph call. Returns (latest full state, interrupt question or None)."""
    question = None
    last = time.perf_counter()
    # "updates" gives {node: changes} after each node; "values" gives the full state,
    # so we don't have to re-apply the reducers ourselves to get the final state.
    for mode, chunk in graph.stream(graph_input, config, stream_mode=["updates", "values"]):
        if mode == "values":
            final_state = chunk
            continue
        if "__interrupt__" in chunk:  # the graph paused in ask_user
            question = chunk["__interrupt__"][0].value
            continue
        now = time.perf_counter()
        # Nodes run one at a time, so the gap between updates is the node's duration.
        for name, changes in chunk.items():
            writer.node(name, changes, (now - last) * 1000)
        last = now
    return final_state, question
