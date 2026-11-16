"""CLI: python -m src.main "How many students are there?" """
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from src.agent.graph import build_graph
from src.agent.llm import get_llm
from src.agent.state import initial_state
from src.db.build_db import DEFAULT_DB_PATH
from src.db.database import connect_readonly
from src.tracing import run_traced

NOTES_PATH = Path(__file__).resolve().parents[1] / "config" / "university_notes.md"


def ask(question: str):
    """Returns (final_state, run_id, trace_path)."""
    engine = connect_readonly(DEFAULT_DB_PATH)
    graph = build_graph(get_llm(), engine, NOTES_PATH.read_text())
    return run_traced(graph, initial_state(question), model=os.getenv("OPENAI_MODEL"))


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit('Usage: python -m src.main "your question"')

    load_dotenv()
    state, run_id, trace_path = ask(sys.argv[1])

    print(f"SQL:\n{state['sql']}\n")
    if state["results"]:
        print(f"Rows returned: {len(state['results'][-1]['rows'])}\n")
    else:  # give_up: attempts was not reset
        print(f"Attempts: {state['attempts']}\n")
    print(f"Status: {state['status']}\n")
    print(f"Answer:\n{state['answer']}\n")
    print(f"Run id: {run_id}")
    trace_path = os.path.relpath(trace_path)
    print(f"Trace:  {trace_path}")
    print(f"View:   python -m src.show_trace {trace_path}")


if __name__ == "__main__":
    main()
