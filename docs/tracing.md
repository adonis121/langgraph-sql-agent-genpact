# Tracing

Every run is traced in two places, both keyed by the same `run_id`:

1. **LangSmith** (when `LANGSMITH_TRACING` / `LANGSMITH_API_KEY` are set in `.env`).
   Runs are named `sql-qa-agent`, tagged `sql-agent`, with metadata `question`, `run_id`, `model`, `thread_id`. A run that pauses for a clarification is two LangSmith runs (before and after the reply) with the same `thread_id`; the local file holds both, with `interrupt` and `resume` events between them.
   The LangSmith run id *is* the local file name, so the two are easy to match.
   Without LangSmith config everything still works; only the local file is written.
2. **Local file** `traces/<run_id>.jsonl`, always written. This is what is kept in the repo.

## How it works
`src/tracing.py` runs the graph with `graph.stream(..., stream_mode=["updates", "values"])`.
- each `"updates"` chunk is `{node_name: changes}` - exactly what the node returned - and becomes one line
- the last `"values"` chunk is the final state, returned to the CLI

The nodes know nothing about tracing: what a node returns is what gets traced.
Each line is flushed right away, so a crash still leaves a partial trace.

Node duration = time between two consecutive updates (nodes run one at a time).

## File format (one JSON object per line)
```
{"run_id", "ts", "event": "start", "question", "model"}
{"run_id", "ts", "event": "node",  "node", "duration_ms", "changes": {...}}   # one per node
{"run_id", "ts", "event": "end",   "status", "answer", "total_ms"}
```
`changes` holds only the state keys the node changed (`sql`, `error`, `attempts`, `last_result`,
`results`, ...). Row lists are cut to the first 20 rows; `row_count` always has the total and
`truncated: true` marks a cut result.

## Reading a trace
```
python -m src.main "How many students are there?"     # prints Run id + Trace path
python -m src.show_trace traces/<run_id>.jsonl
```

## A run with a retry
See `traces/examples/empty-result-retry.jsonl`. The timeline reads:
```
[3] execute_sql     0 rows
[4] check_result    ERROR: Empty result ... empty_retry_used=True   -> back to generate_sql
[5] generate_sql    attempts=2   (same filter: the retry may not change the meaning)
[7] execute_sql     0 rows
[8] check_result    attempts=0, accepted result (0 rows)
[9] answer          "The query returned no matching records." (no LLM call)
```
An SQL error retry looks the same, with the error on `validate_sql` or `execute_sql`
(e.g. `ERROR: Database error: no such column: x`) followed by `generate_sql attempts=2`.
After 3 attempts the next node is `give_up` and the end line has `status=error`.

## What is in git
- `traces/*.jsonl` - ignored (every local run)
- `traces/examples/` - committed, curated real runs (see its README)
