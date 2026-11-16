"""CLI: python -m src.main "How many students are there?" """
import sys
from pathlib import Path

from dotenv import load_dotenv

from src.agent.graph import build_graph
from src.agent.llm import get_llm
from src.agent.state import initial_state
from src.db.build_db import DEFAULT_DB_PATH
from src.db.database import connect_readonly

NOTES_PATH = Path(__file__).resolve().parents[1] / "config" / "university_notes.md"


def ask(question: str) -> dict:
    engine = connect_readonly(DEFAULT_DB_PATH)
    graph = build_graph(get_llm(), engine, NOTES_PATH.read_text())
    return graph.invoke(initial_state(question))


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit('Usage: python -m src.main "your question"')

    load_dotenv()
    state = ask(sys.argv[1])

    print(f"SQL:\n{state['sql']}\n")
    if state["results"]:
        print(f"Rows returned: {len(state['results'][-1]['rows'])}\n")
    print(f"Answer:\n{state['answer']}")


if __name__ == "__main__":
    main()
