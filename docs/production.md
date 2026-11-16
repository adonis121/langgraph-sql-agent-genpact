# Production notes

This is a homework-sized system: one process, a CLI and a small SQLite file. This page lists
what really exists now and what I would add before real users. Nothing in the "Would add"
lists is built.

## Reliability

**Now**
- Fixed workflow: every path ends in `answer`, `give_up`, or `decline`. Max 3 SQL attempts per step and
  max 3 steps, so a run can't loop forever.
- SQL and database errors are caught and fed back to the model. After 3 attempts the user
  gets a give-up message with the last SQL and error, not a stack trace.
- The answer is written only from accepted results. Empty results skip the answer LLM
  ("The query returned no matching records.").
- A planner reply that can't be parsed falls back to one step, and the reason is in the trace.
- 114 tests with a fake LLM (one e2e test per graph path) and a 10-question eval against the real model (9/10).

**Would add**
- Handling for LLM API errors and timeouts inside the graph. Today the OpenAI client's own
  retries are all there is, and a hard failure crashes the run (the partial trace is kept).
- A persistent checkpointer (SQLite or Postgres saver) instead of `InMemorySaver`, so a
  run paused for a clarification survives a restart and can be resumed from another process.
- Run the eval several times per question and track the pass rate, because the model is not deterministic even at temperature 0.
- Run the eval in CI on every prompt change. Prompt edits are code changes.

## Scalability

**Now**
- The schema is read once per graph build, not once per question.
- The full schema goes into every planner and SQL prompt. That works for 6 tables.

**Would add**
- Schema retrieval for big databases: embed table and column descriptions and put only
  the relevant tables (plus their foreign-key neighbours) in the prompt.
- Caching: the schema text per database version, and answers keyed by
  (question, clarification, data version) for repeated questions.
- A statement timeout (Postgres `statement_timeout`, a SQLite progress handler) so one
  expensive query can't block a worker. `LIMIT` caps the rows returned, not the work done.
- A stateless API service (graph built once per process) behind a queue, with workers
  scaled on queue length. The graph itself has no shared mutable state.

## Monitoring

**Now**
- LangSmith: each run is named `sql-qa-agent`, tagged, and has metadata (question, run_id, model, thread_id).
- Local `traces/<run_id>.jsonl` with every node's changes, SQL, rows (cut to 20), timing and
  status, plus `python -m src.show_trace` to read a trace as a timeline.
- `status` on every run: `done`, `error` (give_up), `rejected`, `needs_clarification`.

**Would add**
- Per-run token and cost tracking (LangSmith has it per LLM call; add a total per run and per day).
- Dashboards and alerts on rates: give_up rate, decline rate, clarification rate, empty-answer
  rate, attempts per step, latency p95. A rising give_up rate after a deploy or a schema
  change is the first sign of a broken prompt or schema.
- A sample of real questions reviewed each week and added to the eval set when one is wrong.

## Security

**Now**
- The read-only connection is the boundary: SQLite `mode=ro` + `PRAGMA query_only = ON`.
  A test sends an `INSERT` straight to the DB layer and checks that it fails.
- `validate_sql` as a guardrail: SELECT/WITH only, one statement, no write keywords, LIMIT added.
- The planner declines write requests before any SQL is generated.
- Secrets live in `.env` (git-ignored). `.env.example` has no values.

**Would add**
- A database user with SELECT grants only, on a read replica (never the primary).
- Views that expose only the tables and columns the agent needs (no personal data it
  doesn't need), and row-level security if users may only see their own data.
- A real SQL parser (for example sqlglot) for validation instead of keyword matching: parse to an AST,
  allow only SELECT nodes, allow-list tables.
- Rate limits per user (requests and tokens), and a max question length.
- Traces contain names and grades: decide retention, redact or hash personal data in
  traces, and limit who can open LangSmith.
- Prompt injection through data values: the answer prompt includes database rows. That is low
  risk while the agent can only read, but it should be noted before adding any tool that acts.

## Deployment

**Now**
- Local CLI: `python -m src.main "question"`. Configuration through `.env` (`OPENAI_MODEL`,
  `DATABASE_URL`, `NOTES_PATH`, LangSmith keys).

**Would add**
- A small HTTP API (FastAPI) with `POST /ask` and `POST /resume/{thread_id}` for clarifications,
  using the same `build_graph`. Packaged as a container, with secrets from a secret manager.
- A read-only database branch for the production engine in `connect_readonly` (Postgres:
  read-only user + `default_transaction_read_only`). Nothing in `src/agent` changes.
- Pinned versions in `requirements.txt` (now unpinned) and a lock file.
- Model and prompt version in the run metadata, so any trace shows which prompt produced it.
