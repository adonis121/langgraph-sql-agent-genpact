# SQL validation and security

## What `validate_sql` checks (`src/agent/sql_validation.py`)
1. The query is not empty.
2. It starts with `SELECT` or `WITH`.
3. It is a single statement (no `;` except one at the end).
4. No write keywords: `INSERT, UPDATE, DELETE, DROP, ALTER, CREATE` (whole words, any case).
5. A `LIMIT 200` is added if the query has none.

String literals, quoted identifiers and comments are blanked out before checks 2-5, so
`WHERE status = 'DROPPED'` or a column like `created_at` is not flagged.

A failure is not shown to the user. The message goes back to `generate_sql` together
with the failed SQL, and the model gets another attempt (max 3 per step).

## Why the keyword check is not the security boundary
- **It is a denylist, so it is always incomplete.** SQLite can change things, or reach
  outside the database, without any of the six keywords: `REPLACE`, `ATTACH DATABASE`,
  `PRAGMA` writes, `VACUUM INTO`, `load_extension()`. Other dialects add `COPY`, `GRANT`,
  `MERGE`, `SELECT ... INTO`, and functions with side effects.
- **Text matching does not understand SQL.** It can block valid queries (a name that is a
  keyword) and miss crafted ones.
- **It does nothing about cost.** `LIMIT` caps the rows returned, not the work done: a
  cross join or a huge aggregation still runs in full.

## What actually protects the data
The database connection (`src/db/database.py`, `connect_readonly`):
- the SQLite file is opened with `mode=ro`, so SQLite itself refuses every write
- `PRAGMA query_only = ON` on every connection, as a second layer

`tests/test_database.py::test_writes_are_rejected` shows that an `INSERT` sent straight to
`run_query`, skipping the validator, still fails.

So the validator is a guardrail for correctness: it fails fast with a message the model
can fix, and it keeps results bounded. The read-only connection is the security boundary.

## In production I would add
- a database user with SELECT grants only, on a read replica
- a statement timeout (and, for SQLite, a progress handler) against expensive queries
- views exposing only the tables and columns the agent may see (no personal data it
  doesn't need)

## Known simplifications
- "Has a LIMIT" means a LIMIT anywhere, so a LIMIT inside a subquery counts.
- `LIMIT` is not universal SQL (SQL Server uses `TOP`). It works for SQLite, Postgres
  and MySQL, which is enough for this project.
- If a result hits exactly 200 rows it may be truncated. The answer prompt only sees up to
  50 rows anyway (`MAX_ROWS_IN_PROMPT`).
