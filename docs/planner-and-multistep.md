# Planner, multi-step questions, clarification and running on another database

## The graph

```
START -> plan --answerable--> generate_sql -> validate_sql -> execute_sql -> check_result
          |  ^                    ^     (error loop: max 3 attempts per step, then give_up)   |
          |  |                    +------------- more steps left (step_index + 1) ------------+
          |  +-- ask_user <-- needs_clarification (first time)                                |
          |      [interrupt()]                                        last step accepted -> answer -> END
          +-- out_of_scope, or still unclear after one reply --> decline -> END   (no SQL runs)
```

## The planner: three decisions

`plan` (src/agent/nodes.py) asks the model for one JSON object, checked by the `Plan` model in
src/agent/planner.py:

```json
{"decision": "answerable", "reason": "...", "steps": ["...", "..."], "clarifying_question": null}
```

| decision | when | what happens |
|---|---|---|
| `out_of_scope` | the request changes data (delete, update...), or has nothing to do with the database | `decline` ends with a short message. No SQL is generated. |
| `needs_clarification` | the question is vague in itself ("who is the best teacher?") | `ask_user` pauses the graph and asks; then `plan` runs again with the reply |
| `answerable` | everything else | 1-3 steps, each answered by one SQL query |

Not reasons to ask: several matching records (two students named Maria Garcia) or possible
ties ("the highest average"). Those are answered by listing all of them with their ids.

The whole plan is stored in the state (`plan`), so every trace shows the decision, the
reason and the steps (`python -m src.show_trace ...`).

**Why JSON in the prompt and not `with_structured_output`:** every node talks to the model the
same way, `llm.invoke(prompt).content`. A fake LLM in tests then only has to return strings,
for example `'{"decision": "answerable", ...}'`, then `"SELECT ..."`, then the answer.
`parse_plan` never raises. If the reply can't be read, the question runs as one step, and the
reason (with the start of the raw reply) shows in the trace.

## Clarification with interrupt()

`ask_user` is a separate node with no LLM call:

```python
reply = interrupt(clarifying_question)   # pauses the run; the state is saved by the checkpointer
return {"clarification": reply}          # then back to plan
```

- When LangGraph resumes, it runs the interrupted node again from the top, and `interrupt()`
  returns the reply instead of pausing. If the interrupt were inside `plan`, the planner LLM
  would run a second time and could decide differently. In its own node, running it again
  costs nothing.
- The checkpointer is `InMemorySaver` (part of langgraph). The thread id is the run id.
- `run_traced` (src/tracing.py) does the loop: when it sees `__interrupt__`, it writes an
  `interrupt` event, calls `ask_user(question)` (the CLI uses `input()`), writes a `resume`
  event and streams `Command(resume=reply)` on the same thread, into the same trace file.
- At most one question: if the plan is still unclear after the reply, `decline` ends the run.
- The original `question` is never rewritten. The reply is kept in `clarification` and given
  to the planner and the answer.

## Multi-step questions

`check_result` accepts a step, appends it to `results` and moves `step_index` on. `after_check`
then goes to `generate_sql` for the next step, or to `answer` after the last one. Each step
has its own 3 attempts and its own empty-result retry. For step 2 and later, `generate_sql`
gets a "Results of earlier steps" section: each earlier step's text, SQL and result table.

Example (real run, `traces/examples/multi-step.jsonl`):
"Which teacher had the highest average grade in Fall 2025, and which students failed a course
taught by that teacher"

1. plan -> answerable, 2 steps:
   1. Find the teacher(s) with the highest average grade in Fall 2025, with ids and names.
   2. Find the students who failed any course taught by the teacher(s) from step 1 ...
2. Step 1 SQL groups by teacher and keeps `avg_grade = MAX(avg_grade)`, so ties are kept.
   Result: Priya Shah, id 3.
3. Step 2 SQL is `... WHERE co.teacher_id = 3 ...`, using the id copied from step 1's table.
4. answer sees both tables and writes one answer.

Open point about reading the question: the model reads "failed a course taught by that
teacher" as "in Fall 2025" too. On the seed data this changes the answer: no students in Fall
2025, but in other semesters two students failed one of Priya Shah's courses (Lucas Silva,
Spring 2025; Ethan Miller, Spring 2026). The eval set asks both readings explicitly
(#9 "in any semester", #10 "in Fall 2025"), and both pass. See docs/known-limitations.md.

## Bug found through a trace: `"steps": null`

`traces/examples/bug-planner-null-steps.jsonl`

- **What went wrong:** the multi-step question was answered with one big CTE query. Its
  failure part was limited to Fall 2025, and it had `LIMIT 1` on the top teacher, which
  drops ties.
- **How the trace showed it:** the `plan` node had
  `reason: planner output could not be parsed: Input should be a valid array`, and
  `step 1` was the whole question. So the planner never really ran; the fallback did.
- **Cause:** calling the model with the same prompt showed `"steps": null` (the prompt's JSON
  example used `null` for another field), which the `Plan` model did not accept. The
  reply was `needs_clarification` about ties. That was a second problem, which the fallback
  had hidden.
- **Fix:** `steps: list[str] | None`, and `null` is read as no steps. The prompt says to use
  `[]`. A rule says ties and same-name records are not a reason to ask. The fallback reason
  now includes the start of the raw reply, so the next parse error can be debugged from the
  trace alone. Test: `test_null_steps_are_read_as_no_steps`.

## Running on another database

Nothing in `src/agent` knows about the university. The schema is read with the SQLAlchemy
inspector, the SQL dialect comes from the engine, and the business rules come from a notes
file. Two settings choose the database (src/config.py, from `.env`):

| setting | default |
|---|---|
| `DATABASE_URL` | `sqlite:///db/university.db` |
| `NOTES_PATH` | `config/university_notes.md` |

- **Another SQLite database:** set both settings. Write a notes file with that database's
  rules (what values mean, which values to use for common words). No code change.
- **Another engine (e.g. Postgres):** `connect_readonly` refuses non-SQLite URLs for now,
  because the read-only guarantee is only built for SQLite. To add one, add the driver to
  requirements.txt and a read-only branch in src/db/database.py (a read-only database user,
  or `default_transaction_read_only`). Nothing else changes. `validate_sql` does not depend
  on the dialect.

## Two more findings from real runs

- **Clarification about a shared name.** In one of several runs of "What grades did Maria
  Garcia get?", the planner asked "Which Maria Garcia do you mean?", although the prompt said
  not to. The notes file says names are not unique, which probably invited the question. The
  rule is now explicit ("never ask which one is meant: return all of them with ids"). After
  that, 3 of 3 runs answered both students separately. It is still a prompt rule, so the
  milestone 6 eval set keeps a duplicate-name question.
- **Asking forever on an empty reply.** The CLI hung when stdin had no terminal. Also, an
  empty reply ("") counted as "not asked yet", so the graph could ask again and again.
  Fixed: `after_plan` checks `clarification is None`, so it asks at most once, and the CLI
  treats end of input as an empty reply. An empty reply now ends in `decline`
  (status `needs_clarification`).
