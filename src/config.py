"""Which database and which notes file to use. Read from the environment (.env), with defaults.

This is the only place that points at the university database; src/agent never does.
"""
import os
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.engine import make_url

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE_URL = "sqlite:///db/university.db"
DEFAULT_NOTES_PATH = "config/university_notes.md"


@dataclass(frozen=True)
class Settings:
    database_url: str
    notes_path: Path


def load_settings(env=os.environ) -> Settings:
    """Relative paths (SQLite file, notes file) are resolved from the repo root, not the cwd."""
    return Settings(
        database_url=_resolve_sqlite_path(env.get("DATABASE_URL") or DEFAULT_DATABASE_URL),
        notes_path=_from_repo_root(env.get("NOTES_PATH") or DEFAULT_NOTES_PATH),
    )


def _from_repo_root(path: str) -> Path:
    path = Path(path)
    return path if path.is_absolute() else REPO_ROOT / path


def _resolve_sqlite_path(database_url: str) -> str:
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite" or not url.database:
        return database_url
    return url.set(database=str(_from_repo_root(url.database))).render_as_string(hide_password=False)
