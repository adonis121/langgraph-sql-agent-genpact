"""CLI: python -m src.main "How many students are there?"

The database and the notes file come from src/config.py (DATABASE_URL, NOTES_PATH in .env).
"""
import os
import sys

from dotenv import load_dotenv

from src.agent.graph import build_graph
from src.agent.llm import get_llm
from src.agent.state import initial_state
from src.config import load_settings
from src.db.database import connect_readonly
from src.tracing import run_traced


def ask_in_terminal(question: str) -> str:
    print(f"\nThe agent needs a clarification:\n  {question}")
    try:
        return input("> ")
    except EOFError:  # no terminal (e.g. piped input ran out): continue without a reply
        print("(no reply)")
        return ""


def ask(question: str):
    """Returns (final_state, run_id, trace_path)."""
    settings = load_settings()
    engine = connect_readonly(settings.database_url)
    graph = build_graph(get_llm(), engine, settings.notes_path.read_text())
    return run_traced(graph, initial_state(question), model=os.getenv("OPENAI_MODEL"),
                      ask_user=ask_in_terminal)


def print_result(state: dict) -> None:
    plan = state.get("plan") or {}
    print(f"\nPlan: {plan.get('decision')} - {plan.get('reason')}")
    for result in state["results"]:
        print(f"\nStep {result['step_index'] + 1}: {result['step']}")
        print(f"SQL:\n{result['sql']}")
        print(f"Rows returned: {len(result['rows'])}")
    if state["status"] == "error":  # give_up: show the query that kept failing
        print(f"\nLast SQL tried:\n{state['sql']}\nAttempts: {state['attempts']}")
    print(f"\nStatus: {state['status']}\n")
    print(f"Answer:\n{state['answer']}\n")


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit('Usage: python -m src.main "your question"')

    load_dotenv()
    state, run_id, trace_path = ask(sys.argv[1])

    print_result(state)
    print(f"Run id: {run_id}")
    trace_path = os.path.relpath(trace_path)
    print(f"Trace:  {trace_path}")
    print(f"View:   python -m src.show_trace {trace_path}")


if __name__ == "__main__":
    main()
