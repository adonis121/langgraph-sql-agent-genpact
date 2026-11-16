"""Print a trace file as a readable timeline: python -m src.show_trace traces/<run_id>.jsonl"""
import json
import sys
import textwrap
from pathlib import Path

from src.agent.prompts import format_rows_as_table


def load_trace(path: Path) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def format_trace(records: list[dict]) -> str:
    out = []
    step = 0
    for record in records:
        event = record["event"]
        if event == "start":
            out.append(f"Run {record['run_id']}  model={record.get('model')}")
            out.append(f"Q: {record['question']}\n")
        elif event == "node":
            step += 1
            out.append(f"[{step}] {record['node']:<13} {record['duration_ms']:>8.1f} ms")
            out.extend(_indent(line) for line in describe_changes(record["changes"]))
        elif event == "interrupt":
            out.append(f"\n    -- paused, asked the user: {record['question']}")
        elif event == "resume":
            out.append(f"    -- user replied: {record['reply']}\n")
        elif event == "end":
            out.append(f"\nstatus={record['status']}  total={record['total_ms'] / 1000:.1f} s")
            out.append(f"Answer:\n{_indent(record.get('answer') or '')}")
    return "\n".join(out)


def describe_changes(changes: dict) -> list[str]:
    """One readable line (or block) per changed state key."""
    lines = []
    if changes.get("plan"):
        lines.extend(_plan_lines(changes["plan"]))
    if changes.get("clarification"):
        lines.append(f"clarification: {changes['clarification']}")
    if "attempts" in changes:
        lines.append(f"attempts={changes['attempts']}")
    if changes.get("sql"):
        lines.append("SQL:\n" + _indent(changes["sql"]))
    if changes.get("error"):
        lines.append(f"ERROR: {changes['error']}")
    if changes.get("empty_retry_used"):
        lines.append("empty_retry_used=True")
    if changes.get("last_result"):
        lines.append(_rows_block(changes["last_result"]))
    for entry in changes.get("results", []):
        lines.append(f"accepted result for step {entry['step_index'] + 1} ({entry['row_count']} rows)")
    if changes.get("status"):
        lines.append(f"status={changes['status']}")
    return lines


def _plan_lines(plan: dict) -> list[str]:
    lines = [f"decision={plan['decision']}", f"reason: {plan['reason']}"]
    lines.extend(f"step {i}: {step}" for i, step in enumerate(plan.get("steps") or [], start=1))
    if plan.get("clarifying_question"):
        lines.append(f"clarifying question: {plan['clarifying_question']}")
    return lines


def _rows_block(result: dict) -> str:
    header = f"{result['row_count']} rows"
    if result.get("truncated"):
        header += f" (first {len(result['rows'])} kept in trace)"
    return header + "\n" + _indent(format_rows_as_table(result["columns"], result["rows"]))


def _indent(text: str) -> str:
    return textwrap.indent(text, "    ")


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("Usage: python -m src.show_trace traces/<run_id>.jsonl")
    print(format_trace(load_trace(Path(sys.argv[1]))))


if __name__ == "__main__":
    main()
