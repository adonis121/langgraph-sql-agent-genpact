"""What generate_sql puts in its prompt: schema, notes, dialect, the retry error, earlier results."""
import pytest

from src.agent.nodes import generate_sql
from src.agent.state import initial_state
from src.db.database import schema_as_text
from tests.fake_llm import FakeLLM

STEP = "Count the students"


@pytest.fixture
def call(university_engine, notes):
    """call(**state_changes) -> (node output, prompt sent to the LLM)."""
    schema = schema_as_text(university_engine)

    def run(reply="SELECT COUNT(*) FROM students", **changes):
        fake = FakeLLM([reply])
        state = {**initial_state("Q"), "steps": [STEP], **changes}
        out = generate_sql(state, llm=fake, schema=schema, notes=notes, dialect="sqlite")
        return out, fake.prompts[0]
    return run


def test_first_attempt_has_schema_notes_dialect_and_step(call):
    _, prompt = call()
    assert "Table enrollments" in prompt
    assert "student_id INTEGER NOT NULL -> students.id" in prompt
    assert "Pass mark is 60" in prompt
    assert "sqlite SQL dialect" in prompt
    assert STEP in prompt
    assert "Previous attempt" not in prompt
    assert "Results of earlier steps" not in prompt


def test_retry_shows_the_failed_sql_and_the_error(call):
    _, prompt = call(sql="SELECT nme FROM students", attempts=1,
                     error="Database error: no such column: nme")
    assert "## Previous attempt (failed)" in prompt
    assert "SELECT nme FROM students" in prompt
    assert "no such column: nme" in prompt


def test_later_step_sees_earlier_results(call):
    step_1 = {"step_index": 0, "step": "Teacher with the highest average in Fall 2025",
              "sql": "SELECT t.id, t.name FROM teachers t", "columns": ["id", "name"],
              "rows": [(3, "Priya Shah")]}
    _, prompt = call(steps=[step_1["step"], "Students failed by the teacher from step 1"],
                     step_index=1, results=[step_1])
    assert "## Results of earlier steps" in prompt
    assert "Teacher with the highest average in Fall 2025" in prompt
    assert "SELECT t.id, t.name FROM teachers t" in prompt
    assert "| 3 | Priya Shah |" in prompt
    assert "Students failed by the teacher from step 1" in prompt


def test_reply_is_unfenced_and_attempts_counted(call):
    out, _ = call(reply="```sql\nSELECT 1\n```", attempts=1)
    assert out == {"sql": "SELECT 1", "attempts": 2}
