# Coding agent sessions

This folder contains the full session history with the coding agent used to build this
project, as requested in the submission guidelines.

- **Coding agent:** Claude Code
- **How the sessions were exported:** `/export` at the end of each session, saved as plain text
- **Workflow:** one session per milestone. Each session started in plan mode: the agent
  proposed a plan, I reviewed and adjusted it, then it implemented the milestone. I ran
  and checked the result, then committed.
- **Design decisions** were made before coding and recorded in [`CLAUDE.md`](../../CLAUDE.md),
  which the agent read at the start of every session. They are summarised in
  [00-setup-notes.txt](00-setup-notes.txt).
- I also used Claude (chat) to discuss architecture options and plan the milestones.
  All code was written through Claude Code in the sessions below.
- API keys were removed from the transcripts before committing.

## Sessions

| # | File | Milestone | Key decisions made in this session |
| --- | --- | --- | --- |
| 00 | [00-setup-notes.txt](00-setup-notes.txt) | Design decisions and setup (notes, no code) | Python + LangGraph; fixed workflow instead of a ReAct agent; SQLAlchemy + SQLite; simple SQL validation + read-only connection; LangSmith + local trace files; planner with up to 3 steps |
| 01 | [01-schema-and-seed.txt](01-schema-and-seed.txt) | Schema + seed data | One name column; grade on the enrollment, NULL = ungraded; one section per course per semester; 11 edge cases in the seed data |
| 02 | [02-minimal-graph.txt](02-minimal-graph.txt) | First working graph | Read-only DB in two layers (`mode=ro` + `PRAGMA query_only`); schema read by the inspector; dialect from the engine; `results` reducer; answer node skips the LLM on errors or empty results |
| 03 | [03-validation-retries.txt](03-validation-retries.txt) | Validation, error handling, retries | One pure `validate_sql()` with a test per rule (quotes and comments ignored, so `'DROPPED'` is not flagged); `empty_retry_used` + `last_result` added to the state so `results` holds accepted results only; the empty retry may fix mistakes but never widen a filter; a single all-NULL row counts as empty, COUNT = 0 does not; max 3 attempts, then `give_up` without an LLM call; the keyword check is a guardrail, the read-only DB is the security boundary |
| 04 | [04-tracing.txt](04-tracing.txt) | Tracing | Tracing in its own module: the nodes don't know about it, and what a node returns is what gets traced (`stream_mode="updates"`); LangSmith run id = local file name; rows cut to 20 with `row_count`; `show_trace` timeline; `traces/*.jsonl` git-ignored, curated `traces/examples/` committed; no faked traces for paths that didn't happen; found that "Delete all students..." was answered with a SELECT, which became input for the planner |
| 05 | [05-planner.txt](05-planner.txt) | Multi-step planner, clarification, DB-agnostic config | Planner with 3 decisions and the whole plan kept in the state; JSON in the prompt + Pydantic instead of `with_structured_output`; `ask_user` as a separate node with `interrupt()` + `InMemorySaver`, at most one question; ties and same-name records are not reasons to ask; `DATABASE_URL` / `NOTES_PATH` in `src/config.py`, non-SQLite URLs refused; **bug found through a trace:** `"steps": null` made the planner fall back to one step |
| 06 | [06-test-and-eval.txt](06-test-and-eval.txt) | Unit tests + evaluation set | Fake LLM that returns scripted strings and fails on an unscripted call; one e2e test per graph path that checks the exact node sequence; eval compares results, not SQL (columns picked, rows as sets, numbers rounded); reference queries tested in pytest; first run 6/10 → 3 references were wrong (read in the traces) and fixed → 9/10; #6 left as a real miss |
| 07 | [07-docs.txt](07-docs.txt) | Documentation, examples, traces | Root README with a mermaid diagram generated from the compiled graph; examples only from real traces (3 new runs recorded with the planner); honest production notes (now vs would add) and known limitations; every README command checked in a clean copy |

## Where to look first

- **How the architecture was chosen:** 00 and 02
- **How problems were found and fixed:** 05 (the `"steps": null` planner bug found through a
  trace, the Maria Garcia clarification, the endless clarification loop on an empty reply) and 06 (the
  first eval run at 6/10: the failures were read in their traces and 3 turned out to be reference mistakes)
- **Validation and security reasoning:** 03
