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
| 01 | [01-schema-and-seed.txt](01-schema-and-seed.txt) | Schema + seed data | 
one name column; 
grade on enrollment, 
NULL = ungraded; one section per course per semester;
11 edge cases in the seed data”|
| 02 | [02-minimal-graph.txt](02-minimal-graph.txt) | First working graph | read-only DB in two layers; 
schema read by the inspector; dialect from the engine; 
results reducer; answer node skips the LLM on errors or empty results”|
| 03 | [03-validation-and-retries.txt](03-validation-and-retries.txt) | Validation, error handling, retries | |
| 04 | [04-tracing.txt](04-tracing.txt) | Tracing | |
| 05 | [05-planner-and-db-agnostic.txt](05-planner-and-db-agnostic.txt) | Multi-step planner, clarification, DB-agnostic config | |
| 06 | [06-tests-and-evals.txt](06-tests-and-evals.txt) | Unit tests + evaluation set | |
| 07 | [07-docs.txt](07-docs.txt) | Documentation, examples, traces | |

## Where to look first

- **How the architecture was chosen:** 00 and 02
- **How problems were found and fixed:** <!-- fill in: the session where you debugged a real issue -->
