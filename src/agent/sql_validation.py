"""Check generated SQL before it runs. A pure function: no LLM, no database.

This is a guardrail for the model (fast, clear errors it can fix), not the security
boundary. Writes are blocked for real by the read-only connection in src/db/database.py.
"""
import re

ROW_LIMIT = 200
WRITE_KEYWORDS = ("INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE")

# String literals, quoted identifiers and comments. They are blanked out before the
# checks, so a value like 'DROPPED' or a comment like "-- delete later" is not flagged.
_LITERALS_AND_COMMENTS = re.compile(
    r"'(?:[^']|'')*'"       # 'string', with '' as an escaped quote
    r'|"(?:[^"]|"")*"'      # "quoted identifier"
    r"|--[^\n]*"            # -- line comment
    r"|/\*.*?\*/",          # /* block comment */
    re.DOTALL,
)
_WRITE_PATTERN = re.compile(r"\b(" + "|".join(WRITE_KEYWORDS) + r")\b", re.IGNORECASE)


def validate_sql(sql: str, row_limit: int = ROW_LIMIT) -> str:
    """Return the SQL ready to run (with a LIMIT), or raise ValueError saying what is wrong."""
    sql = sql.strip().removesuffix(";").rstrip()
    if not sql:
        raise ValueError("Query is empty.")

    code = _LITERALS_AND_COMMENTS.sub(" ", sql)

    first_word = code.split(maxsplit=1)[0].upper() if code.strip() else ""
    if first_word not in ("SELECT", "WITH"):
        raise ValueError(f"Only SELECT or WITH queries are allowed, got: {first_word or 'nothing'}.")

    if ";" in code:
        raise ValueError("Only one statement is allowed; remove the ';' between statements.")

    write = _WRITE_PATTERN.search(code)
    if write:
        raise ValueError(f"Write keyword not allowed: {write.group(1).upper()}.")

    if not re.search(r"\bLIMIT\b", code, re.IGNORECASE):
        # Newline, not space: the query may end with a -- comment.
        sql = f"{sql}\nLIMIT {row_limit}"
    return sql
