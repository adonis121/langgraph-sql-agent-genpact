"""All prompts in one place, plus the helpers that format data into them."""

MAX_ROWS_IN_PROMPT = 50

GENERATE_SQL_PROMPT = """You translate questions about a university database into SQL.

Write exactly one read-only SELECT query in the {dialect} SQL dialect that answers the question.
Use only the tables and columns in the schema. Return only the SQL, no explanation.

## Schema
{schema}

## Business rules
{notes}

## Question
{question}
{retry}"""

# Appended to GENERATE_SQL_PROMPT when the previous attempt for this step failed.
RETRY_SECTION = """
## Previous attempt (failed)
SQL:
{sql}

Problem: {error}

Write a corrected query.
"""

# The error check_result reports for an empty result. It must not invite the model to
# change the question: an empty result can be the correct answer.
EMPTY_RETRY_HINT = """Empty result: the query ran but returned no rows (or only NULLs).
This may be the correct answer. Check only for mistakes:
- a literal value spelled or cased differently from the data (see business rules)
- a wrong join path or wrong column
Do NOT change the meaning of the question: never widen, loosen or remove a filter
(e.g. do not turn "= 100" into ">= 90"). If the query already matches the question,
return it unchanged."""

ANSWER_PROMPT = """You answer a question using ONLY the query result below.

Rules:
- Use only the rows in the result table. Do not add facts, names or numbers that are not in it.
- Copy numbers exactly as shown (round to at most 2 decimals). Do not recompute them.
- If the result does not answer the question, say so plainly.
- Use the business rules only to interpret the values (e.g. what an empty grade means).
- Be short and direct.

## Business rules
{notes}

## Question
{question}

## SQL that was run
{sql}

## Query result
{table}
"""

EMPTY_ANSWER = "The query returned no matching records."

GIVE_UP_ANSWER = """Sorry, I couldn't answer this question after {attempts} attempts.
Last SQL tried:
{sql}
Last error: {error}
Try rephrasing the question or naming the table/field you mean."""


def format_rows_as_table(columns: list[str], rows: list[tuple]) -> str:
    """Render rows as a markdown table, truncated to MAX_ROWS_IN_PROMPT rows."""
    shown = rows[:MAX_ROWS_IN_PROMPT]
    lines = [
        "| " + " | ".join(columns) + " |",
        "|" + "---|" * len(columns),
        *("| " + " | ".join(_cell(v) for v in row) + " |" for row in shown),
    ]
    if len(rows) > len(shown):
        lines.append(f"(showing {len(shown)} of {len(rows)} rows)")
    return "\n".join(lines)


def _cell(value) -> str:
    return "NULL" if value is None else str(value)
