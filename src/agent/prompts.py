"""All prompts in one place, plus the helpers that format data into them."""

MAX_ROWS_IN_PROMPT = 50

PLAN_PROMPT = """You plan how to answer a question about the database described below.
You do not write SQL. Decide one of three things:

- "out_of_scope": the request asks to change data (insert, update, delete, drop, create...),
  or it has nothing to do with the data in this database.
- "needs_clarification": the question is vague in itself, so no query can answer it as asked,
  e.g. it uses a subjective word like "best" or "good" with no measure. Then write ONE short
  clarifying question.
  NOT vague, so never ask about them:
  - a measurable criterion, e.g. "the highest average", "the most", "fewer than 3". Ties are
    possible but not a reason to ask: the step returns all tied rows.
  - a name that several records share, e.g. two people with the same name. Never ask which
    one is meant: plan steps that return all of them, each with its id.
- "answerable": anything else. Split it into steps:
  - Use 1 step unless a later part needs the result of an earlier part, or the question has
    separate parts. At most 3 steps.
  - Each step is one self-contained question in plain words (not SQL) that one query can answer.
  - Keep the user's filters exactly: never add, drop or widen a filter (a semester, a course,
    a grade limit...). A later step refers to "the <thing> from step N".
  - Ask each step to return, for every person or thing it lists, both its id and its readable
    name, so rows of different records with the same name stay apart and the answer can use names.
{clarification_rule}
Reply with only one JSON object, no other text:
{{"decision": "...", "reason": "one short sentence", "steps": ["..."], "clarifying_question": "..."}}
Use [] for steps when the decision is not "answerable", and null for clarifying_question
when there is nothing to ask.

## Schema
{schema}

## Business rules
{notes}

## Question
{question}
{clarification}"""

# Added to PLAN_PROMPT after the user answered the clarifying question.
CLARIFICATION_SECTION = """
## The user's clarification
{clarification}
"""
CLARIFICATION_GIVEN_RULE = """
The user has already answered one clarifying question. Do not ask another one: use their
clarification, or choose "out_of_scope" if the question still cannot be answered from the data.
"""

GENERATE_SQL_PROMPT = """You translate questions about a database into SQL.

Write exactly one read-only SELECT query in the {dialect} SQL dialect that answers the question.
Use only the tables and columns in the schema. Return only the SQL, no explanation.

## Schema
{schema}

## Business rules
{notes}

{previous_steps}
## Question
{question}
{retry}"""

# Added to GENERATE_SQL_PROMPT from step 2 on: the accepted results of earlier steps.
PREVIOUS_STEPS_SECTION = """
## Results of earlier steps
Use values from these results (e.g. ids) as literals in your query where the question
refers to them.

{steps}
"""

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

ANSWER_PROMPT = """You answer a question using ONLY the query results below.

Rules:
- Use only the rows in the result tables. Do not add facts, names or numbers that are not in them.
- Copy numbers exactly as shown (round to at most 2 decimals). Do not recompute them.
- If the results do not answer the question (or a part of it), say so plainly.
- Use the business rules only to interpret the values (e.g. what an empty grade means).
- Refer to people by name (and id when names repeat), not by he/she.
- Be short and direct.

## Business rules
{notes}

## Question
{question}
{clarification}
## Steps that were run
{steps}
"""

EMPTY_ANSWER = "The query returned no matching records."

OUT_OF_SCOPE_ANSWER = """I can't help with that: {reason}
I can only answer questions that read data from this database; I never change it."""

STILL_UNCLEAR_ANSWER = """I still couldn't turn this into a query: {reason}
Please ask again with a measurable criterion."""

GIVE_UP_ANSWER = """Sorry, I couldn't answer this question after {attempts} attempts.
Last SQL tried:
{sql}
Last error: {error}
Try rephrasing the question or naming the table/field you mean."""


def format_step_results(results: list[dict]) -> str:
    """Each accepted step as: step text, its SQL and its result table."""
    return "\n\n".join(
        f"### Step {r['step_index'] + 1}: {r['step']}\n"
        f"SQL:\n{r['sql']}\n\n"
        f"Result:\n{format_rows_as_table(r['columns'], r['rows'])}"
        for r in results
    )


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
