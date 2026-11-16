# Example traces

Real runs (gpt-4.1-mini), copied from `traces/` by hand. Everyday runs in `traces/*.jsonl`
are git-ignored; only these curated examples are committed.

| File | Question | What it shows |
|---|---|---|
| `aggregation-failed-students.jsonl` | How many students failed at least one course? | Planner -> 1 step, pass-mark rule from the notes file (grade < 60, NULL excluded) |
| `join-teacher-semester.jsonl` | Which courses did Daniel Kim teach in Spring 2026? | Join over 4 tables with teacher and semester filters (a student has the same name) |
| `empty-result-two-steps.jsonl` | Which students took the course Quantum Basket Weaving? | With the planner: 2 steps, each empty -> one retry with the same filter -> accepted -> "no matching records" without an LLM call |
| `simple-success.jsonl` | How many students are there? | (milestone 4, before the planner) Happy path: generate -> validate (LIMIT added) -> execute -> check -> answer |
| `out-of-scope-delete.jsonl` | Delete all students who failed a course | Planner says `out_of_scope` -> decline. No SQL is generated or run (in milestone 4 this produced a SELECT and "Delete students with these IDs") |
| `multi-step.jsonl` | Which teacher had the highest average grade in Fall 2025, and which students failed a course taught by that teacher | 2 steps; step 2's SQL uses `teacher_id = 3` taken from step 1's result |
| `clarification-interrupt.jsonl` | Who is the best teacher? | `needs_clarification` -> paused with interrupt() -> user replied "the highest average grade in Fall 2025" -> plan again -> answered |
| `duplicate-names.jsonl` | What grades did Maria Garcia get? | Two students share the name: no clarification, the answer lists both by id |
| `bug-planner-null-steps.jsonl` | (the multi-step question) | Bug found through the trace: the planner reply had `"steps": null`, failed to parse, and the fallback ran the whole question as one step. See docs/planner-and-multistep.md |
| `empty-result-retry.jsonl` | Which students took the course Quantum Basket Weaving? | (milestone 4, before the planner) Empty result -> one retry with the hint -> model keeps the same filter -> second empty result accepted -> "no matching records" without an LLM call |

View one with: `python -m src.show_trace traces/examples/empty-result-retry.jsonl`

Walked through with SQL, results and answers in [docs/examples.md](../../docs/examples.md).

Still to add when they happen in real runs: an SQL-error retry and a give_up (both are
covered by e2e tests with the fake LLM in `tests/test_graph_e2e.py`).
