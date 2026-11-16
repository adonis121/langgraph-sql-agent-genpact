# Project: University QA Agent (Genpact homework)

## Goal
A question-answering system over a university SQL database. Users ask questions in
natural language; a LangGraph agent turns them into SQL, runs the SQL, and returns a
human-readable answer. It must handle aggregations, joins, filters (semester, course,
teacher, student) and multi-step reasoning.

## Stack
- Python 3.11 (venv in ./venv)
- LangGraph + langchain-openai (OpenAI model, key in .env)
- SQLAlchemy + SQLite
- pytest
- LangSmith for tracing (env vars in .env)

## Database
Core entities: teachers, students, courses.
- A course is taught by a teacher in a specific semester -> course_offerings table
- Students enroll in course offerings -> enrollments table
- Students receive grades for enrolled courses (grade lives on the enrollment)
- Every student and teacher has a name
Keep the schema clean and explainable. Seed data should be realistic and include edge
cases (e.g. ungraded/current semester, failing grades, two people with the same name).

## Graph design (fixed workflow, not a ReAct agent)
plan -> generate_sql -> validate_sql -> execute_sql -> check_result -> answer

- plan: decide if the question is answerable or too vague (then end with a clarifying
  message), and split it into 1-3 sub-questions (steps)
- generate_sql: write ONE SQL query for the current step; later steps get the results
  of earlier steps
- validate_sql / execute_sql / check_result: on failure, loop back to generate_sql with
  the error message (max 3 attempts per step), then go to a give_up node
- check_result: an empty result gets one retry; after the last step go to answer
- answer: write the answer only from the actual query results

## State (TypedDict)
question, steps, step_index, sql, error, attempts, empty_retry_used, last_result, results,
answer, status
- empty_retry_used: the one empty-result retry was used in the current step
- last_result: rows from execute_sql waiting for check_result; only check_result appends to
  results, so results holds accepted results only

## Rules
- DB-agnostic: no table or column names in agent code. The schema is read from the
  database with the SQLAlchemy inspector. University-specific notes (descriptions,
  business rules) live in one separate config file.
- SQL validation (simple): only SELECT/WITH, a single statement, no write keywords
  (INSERT, UPDATE, DELETE, DROP, ALTER, CREATE), add a LIMIT if missing.
  The database connection is opened read-only (PRAGMA query_only = ON).
- Every node returns only the state keys it changes.
- Prompts live in one place, not scattered across nodes.
- Tests use a fake LLM (no API calls): DB queries and joins, SQL generation,
  end-to-end graph behaviour.
- Tracing: LangSmith, plus each node's output written to traces/<run_id>.jsonl so the
  full path (input -> nodes -> SQL -> DB results -> answer) is saved in the repo.
- Keep the code simple, modular and easy to explain in an interview.
  Clear names, short functions, comments only where the reason isn't obvious.

## Evaluation criteria (from the homework) - every decision should serve these
correctness, clarity of design, ability to handle complex questions, quality of
LangGraph usage, traceability and debuggability, code cleanliness and structure,
ability to explain and defend the system. "Small, working, explainable" beats big.

## Planned additions driven by the criteria
- Ambiguous questions: pause the graph with LangGraph interrupt() + a checkpointer,
  ask the user, and resume with their answer (milestone 5).
- Correctness: an eval set of 8-10 questions with hand-written reference SQL; compare
  the agent's RESULTS (not SQL text) to the reference results (milestone 6).
- Debuggability: document at least one real bug found through a trace in docs/
  (what went wrong, how the trace showed it, the fix) and add it to the eval set.
- Validation: one clear validate_sql function with a test per rule.
- Not in scope: web UI, multiple databases, anything we can't explain.

## Submission
- Public GitHub repo: langgraph-sql-agent-genpact
- Session history with the coding agent is REQUIRED: export every Claude Code session
  with /export to docs/agent-sessions/NN-<milestone>.txt (check for API keys first).
- Keep requirements.txt up to date when adding a package.

## Folders
db/        schema.sql, seed.sql
src/       agent (graph, nodes, state, prompts), db layer, tracing
tests/
traces/
docs/      design decisions, production notes, examples

## Working agreement
Work milestone by milestone. Propose a plan before writing code. Don't add features
that weren't asked for in the current milestone.
