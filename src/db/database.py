"""Read-only database access: connect, describe the schema as text, run a query.

Nothing here knows table or column names; the schema is read with the SQLAlchemy inspector.
"""
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import Engine, create_engine, event, inspect, text


@dataclass
class QueryResult:
    columns: list[str]
    rows: list[tuple]


def connect_readonly(db_path: Path) -> Engine:
    """Open a SQLite file read-only: mode=ro at the file level, plus PRAGMA query_only."""
    db_path = Path(db_path).resolve()
    if not db_path.exists():
        raise FileNotFoundError(f"{db_path} not found. Build it with: python -m src.db.build_db")

    engine = create_engine(f"sqlite:///file:{db_path}?mode=ro&uri=true")

    @event.listens_for(engine, "connect")
    def _set_query_only(dbapi_conn, _record):
        dbapi_conn.execute("PRAGMA query_only = ON")

    return engine


def schema_as_text(engine: Engine) -> str:
    """Describe every table (columns, keys, constraints) in a compact text block for the prompt."""
    inspector = inspect(engine)
    return "\n\n".join(
        _describe_table(inspector, table) for table in inspector.get_table_names()
    )


def _describe_table(inspector, table: str) -> str:
    pk_columns = set(inspector.get_pk_constraint(table)["constrained_columns"])
    foreign_keys = {
        fk["constrained_columns"][0]: f'{fk["referred_table"]}.{fk["referred_columns"][0]}'
        for fk in inspector.get_foreign_keys(table)
    }
    uniques = inspector.get_unique_constraints(table)
    single_uniques = {u["column_names"][0] for u in uniques if len(u["column_names"]) == 1}

    lines = [f"Table {table}"]
    for column in inspector.get_columns(table):
        name = column["name"]
        parts = [name, str(column["type"])]
        if name in pk_columns:
            parts.append("PK")
        else:
            parts.append("NULL" if column["nullable"] else "NOT NULL")
        if name in single_uniques:
            parts.append("UNIQUE")
        if name in foreign_keys:
            parts.append(f"-> {foreign_keys[name]}")
        lines.append("  " + " ".join(parts))

    for unique in uniques:
        if len(unique["column_names"]) > 1:
            lines.append(f'  UNIQUE ({", ".join(unique["column_names"])})')
    for check in inspector.get_check_constraints(table):
        lines.append(f'  CHECK ({check["sqltext"]})')
    return "\n".join(lines)


def run_query(engine: Engine, sql: str) -> QueryResult:
    """Run one SQL statement and return column names and rows. Errors are raised to the caller."""
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        return QueryResult(columns=list(result.keys()), rows=[tuple(row) for row in result])
