# Known limitations

Everything here was seen in real runs or follows from the code. None of it is fixed.

## Answers and reasoning

- **The multi-step question can be read two ways.** In "Which teacher had the highest
  average grade in Fall 2025, and which students failed a course taught by that teacher",
  the model always reads the second part as "in Fall 2025" too. With that reading nobody
  failed. In any semester, two students did (Lucas Silva, Spring 2025; Ethan Miller,
  Spring 2026). See [traces/examples/multi-step.jsonl](../traces/examples/multi-step.jsonl).
  The planner does not ask, because the question is not vague in itself. The eval avoids the
  ambiguity by asking both versions explicitly (#9 "in any semester", #10 "in Fall 2025"). Both pass.
- **The planner can drop a column the question asks for.** Eval #6 ("List every failing
  grade with the student, the course code and the semester") fails: the planner rewrote
  the step without the grade, and this happened the same way on two runs. See
  [eval-report.md](eval-report.md).
- **An empty step does not stop the run.** If step 1 returns nothing, step 2 still runs,
  with its own empty-result retry. For "Which students took the course Quantum Basket
  Weaving?" that meant 4 SQL generations for a course that doesn't exist
  ([traces/examples/empty-result-two-steps.jsonl](../traces/examples/empty-result-two-steps.jsonl)).
  The answer is still correct, but it costs more calls.
- **Prompt rules are not guarantees.** "Never ask which of two same-name people is meant" and
  "never widen a filter on retry" are instructions to the model. They held in the runs
  we checked (3 of 3 for Maria Garcia after the rule was made stronger), but nothing enforces them in code.
- **Later steps copy ids through the prompt.** Step 2 sees step 1's result as a table of at
  most 50 rows (`MAX_ROWS_IN_PROMPT`) and copies the ids into its SQL. If step 1 has more
  than 50 rows, step 2 is told "(showing 50 of N rows)" but can't see the rest.
- **Model-written ordering can be wrong.** In the duplicate-names trace the model sorted by
  `s.year, s.term`, and `term` is text, so Spring 2025 came after Fall 2025. The answer
  still listed the right grades.
- **At most one clarification.** If the reply is still unclear (or empty), the run ends in
  `decline`. There is no second question.

## Evaluation

- **The comparison is lenient** ([src/eval/compare.py](../src/eval/compare.py)): extra agent
  columns are allowed, column names and order are ignored, rows are compared as sets
  (duplicates are ignored), numbers are rounded to 2 decimals, and only the **last** step's
  rows are checked. The answer text is not checked at all, so a correct result with a wrong
  sentence would pass.
- **And strict in other ways:** values must match exactly, so a course given by code where
  the reference uses the title fails. The reference shape for #6 is one reason it fails.
- **One run per question:** 9/10 is one sample, and the variation between runs is not measured.
- **Ties in the reference:** the "best teacher" part of the #9 and #10 references uses `ORDER BY
  AVG(grade) DESC LIMIT 1`, so it would drop a tie. There is no tie in the seed data, so this does not matter for the current
  score. The agent itself keeps ties (`= MAX(...)`).
- 10 questions on one small seeded database. This shows the main paths work. It is not a benchmark.

## Database and SQL

- **The read-only guarantee exists only for SQLite.** `connect_readonly` refuses other
  engines instead of opening a connection that could write. Another engine needs its own
  read-only setup (see [planner-and-multistep.md](planner-and-multistep.md#running-on-another-database)).
- **`LIMIT` is not universal SQL.** SQL Server uses `TOP`. The validator adds `LIMIT 200`,
  which works on SQLite, Postgres and MySQL.
- **"Has a LIMIT" means a LIMIT anywhere**, so a LIMIT in a subquery stops the outer LIMIT from being added.
- **200-row cap:** a result of exactly 200 rows may have been cut by the added `LIMIT`, and
  nothing tells the model so. Beyond 50 rows, the answer prompt shows the first 50 with
  "(showing 50 of N rows)".
- **The keyword check is a denylist.** It misses `REPLACE`, `ATTACH`, `PRAGMA`... The read-only
  connection is what protects the data
  ([sql-validation-and-security.md](sql-validation-and-security.md)).
- **No statement timeout.** An expensive query runs to the end.
- **The full schema goes into every prompt.** This is fine for 6 tables, not for hundreds.

## Runtime

- **`InMemorySaver`:** a run paused for a clarification only lives in the current process.
- **LLM API errors are not handled in the graph.** A hard OpenAI failure ends the run with an
  exception. The partial trace is kept.
- **No real-run example of an SQL-error retry or a give_up.** gpt-4.1-mini wrote valid SQL in every run
  we tried. Both paths are covered by e2e tests with the fake LLM
  ([tests/test_graph_e2e.py](../tests/test_graph_e2e.py)), and we did not fake a trace.
