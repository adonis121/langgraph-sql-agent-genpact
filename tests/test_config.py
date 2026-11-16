"""Settings: defaults, env overrides, paths resolved from the repo root."""
import pytest

from src.config import REPO_ROOT, load_settings
from src.db.database import connect_readonly


def test_defaults_point_at_the_university_db_and_notes():
    settings = load_settings({})
    assert settings.database_url == f"sqlite:///{REPO_ROOT / 'db' / 'university.db'}"
    assert settings.notes_path == REPO_ROOT / "config" / "university_notes.md"


def test_env_overrides_both(tmp_path):
    settings = load_settings({"DATABASE_URL": f"sqlite:///{tmp_path / 'shop.db'}",
                              "NOTES_PATH": str(tmp_path / "shop_notes.md")})
    assert settings.database_url == f"sqlite:///{tmp_path / 'shop.db'}"
    assert settings.notes_path == tmp_path / "shop_notes.md"


def test_relative_paths_are_from_the_repo_root():
    settings = load_settings({"DATABASE_URL": "sqlite:///data/other.db", "NOTES_PATH": "notes.md"})
    assert settings.database_url == f"sqlite:///{REPO_ROOT / 'data' / 'other.db'}"
    assert settings.notes_path == REPO_ROOT / "notes.md"


def test_non_sqlite_url_is_refused_until_read_only_is_built():
    with pytest.raises(NotImplementedError, match="postgresql"):
        connect_readonly("postgresql://user@localhost/db")
