"""Shared fixtures for the agent tests: the real seeded test DB, the notes file, a graph builder."""
import pytest

from src.agent.graph import build_graph
from src.config import load_settings
from src.db.build_db import build_database
from src.db.database import connect_readonly
from tests.fake_llm import FakeLLM


@pytest.fixture(scope="session")
def university_engine(tmp_path_factory):
    path = tmp_path_factory.mktemp("agent_db") / "university.db"
    build_database(path)
    engine = connect_readonly(f"sqlite:///{path}")
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def notes():
    return load_settings({}).notes_path.read_text()  # the default notes file


@pytest.fixture
def make_graph(university_engine, notes):
    """make_graph(replies) -> (compiled graph, fake LLM)."""
    def make(replies):
        fake = FakeLLM(replies)
        return build_graph(fake, university_engine, notes), fake
    return make
