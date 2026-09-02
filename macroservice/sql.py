from __future__ import annotations

from pathlib import Path

DB_DIR = Path(__file__).parent.parent / "db"
QUERY_DIR = DB_DIR / "queries"
MIGRATION_DIR = DB_DIR / "migrations"


def load_query(*parts: str) -> str:
    """Load a UTF-8 SQL query from db/queries/."""
    return (QUERY_DIR.joinpath(*parts)).read_text(encoding="utf-8")


def load_migration(path: Path) -> str:
    """Load one migration script."""
    return path.read_text(encoding="utf-8")