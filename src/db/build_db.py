"""Build the SQLite database from db/schema.sql and db/seed.sql.

Run from the repo root:  python -m src.db.build_db
"""
import sqlite3
from pathlib import Path

DB_DIR = Path(__file__).resolve().parents[2] / "db"
SCHEMA_PATH = DB_DIR / "schema.sql"
SEED_PATH = DB_DIR / "seed.sql"
DEFAULT_DB_PATH = DB_DIR / "university.db"


def build_database(db_path: Path = DEFAULT_DB_PATH) -> dict[str, int]:
    """Create a fresh database at db_path and return the row count per table."""
    db_path = Path(db_path)
    db_path.unlink(missing_ok=True)

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(SCHEMA_PATH.read_text())
        conn.executescript(SEED_PATH.read_text())
        conn.commit()
        return table_row_counts(conn)
    finally:
        conn.close()


def table_row_counts(conn: sqlite3.Connection) -> dict[str, int]:
    tables = [row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
    )]
    return {t: conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in tables}


if __name__ == "__main__":
    counts = build_database()
    print(f"Built {DEFAULT_DB_PATH}")
    for table, count in counts.items():
        print(f"  {table:<18} {count}")
