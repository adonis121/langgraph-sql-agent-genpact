# Example traces

Real runs (gpt-4.1-mini), copied from `traces/` by hand. Everyday runs in `traces/*.jsonl`
are git-ignored; only these curated examples are committed.

| File | Question | What it shows |
|---|---|---|
| `simple-success.jsonl` | How many students are there? | Happy path: generate -> validate (LIMIT added) -> execute -> check -> answer |
| `empty-result-retry.jsonl` | Which students took the course Quantum Basket Weaving? | Empty result -> one retry with the hint -> model keeps the same filter -> second empty result accepted -> "no matching records" without an LLM call |

View one with: `python -m src.show_trace traces/examples/empty-result-retry.jsonl`

Still to add when they happen in real runs: an SQL-error retry, a give_up, and the bug
found through a trace (see CLAUDE.md, debuggability).
