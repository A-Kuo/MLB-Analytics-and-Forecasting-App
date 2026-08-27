"""Tests for macroservice/db.py -- the generic Postgres connection/schema
utilities shared by every domain that caches data in this app's Neon
instance (roster history, PyTorch team forecasts, season stats).

Mocks the SQLAlchemy Engine/Connection rather than touching a real
database, matching how the rest of the suite mocks request_with_backoff
instead of calling the live MLB API.
"""
from __future__ import annotations

from unittest.mock import MagicMock

from macroservice import db


def _writable_engine():
    """An Engine whose begin() context yields a recording connection."""
    engine = MagicMock()
    conn = engine.begin.return_value.__enter__.return_value
    return engine, conn


# ---------------------------------------------------------------------------
# ensure_schema
# ---------------------------------------------------------------------------


def test_ensure_schema_executes_the_schema_file():
    engine, conn = _writable_engine()
    db.ensure_schema(engine)
    executed = str(conn.execute.call_args[0][0])
    assert "CREATE TABLE IF NOT EXISTS players" in executed
    assert "CREATE TABLE IF NOT EXISTS roster_stints" in executed


def test_schema_file_exists_at_the_expected_path():
    assert db.SCHEMA_PATH.is_file()


def test_schema_file_has_no_stray_bind_parameters():
    # SQLAlchemy's text() treats any ":word" in the SQL -- including inside
    # a "-- comment" -- as a bind parameter placeholder it expects a value
    # for. A schema.sql comment mentioning e.g. "WHERE track = :track" would
    # compile "successfully" (mocked-connection tests can't catch this) but
    # fail at real-execute time with "A value is required for bind parameter
    # 'track'". Compiling for real (no mock, no live DB needed) is the only
    # way to catch it. Covers every table across every domain, since they
    # all share this one schema.sql file.
    from sqlalchemy import text

    compiled = text(db.SCHEMA_PATH.read_text()).compile()
    assert compiled.params == {}


# ---------------------------------------------------------------------------
# normalize_database_url / resolve_database_url
# ---------------------------------------------------------------------------


def test_normalize_rewrites_bare_postgresql_scheme_to_psycopg3():
    # The form Neon's dashboard hands out -- SQLAlchemy would otherwise
    # reach for psycopg2, which this project doesn't install.
    assert db.normalize_database_url("postgresql://u:p@host/db").startswith("postgresql+psycopg://")


def test_normalize_rewrites_legacy_postgres_scheme():
    assert db.normalize_database_url("postgres://u:p@host/db") == "postgresql+psycopg://u:p@host/db"


def test_normalize_preserves_the_rest_of_the_url():
    normalized = db.normalize_database_url("postgresql://u:p@host/db?sslmode=require")
    assert normalized == "postgresql+psycopg://u:p@host/db?sslmode=require"


def test_normalize_leaves_an_already_correct_url_alone():
    url = "postgresql+psycopg://u:p@host/db"
    assert db.normalize_database_url(url) == url


def test_normalize_accepts_a_full_toml_block():
    # The Streamlit-secrets shape pasted where a bare URL was expected --
    # e.g. into the GitHub Actions DATABASE_URL secret.
    block = '[connections.postgresql]\nurl = "postgresql://u:p@host/db"\n'
    assert db.normalize_database_url(block) == "postgresql+psycopg://u:p@host/db"


def test_normalize_ignores_a_toml_block_without_a_url_key():
    assert db.normalize_database_url("[connections.postgresql]\n") == "[connections.postgresql]"


def test_resolve_prefers_the_environment_variable(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://env-host/db")
    assert db.resolve_database_url() == "postgresql+psycopg://env-host/db"


def test_resolve_falls_back_to_secrets_file(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    secrets = tmp_path / "secrets.toml"
    secrets.write_text('[connections.postgresql]\nurl = "postgresql://file-host/db"\n')
    monkeypatch.setattr(db, "SECRETS_PATH", secrets)
    assert db.resolve_database_url() == "postgresql+psycopg://file-host/db"


def test_resolve_returns_none_when_secrets_file_is_malformed(monkeypatch, tmp_path):
    # A bare connection string pasted without the TOML wrapper -- an easy
    # setup mistake that must not raise from inside the resolver.
    monkeypatch.delenv("DATABASE_URL", raising=False)
    secrets = tmp_path / "secrets.toml"
    secrets.write_text("postgresql://not-valid-toml/db\n")
    monkeypatch.setattr(db, "SECRETS_PATH", secrets)
    assert db.resolve_database_url() is None


def test_resolve_returns_none_when_nothing_is_configured(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(db, "SECRETS_PATH", tmp_path / "missing.toml")
    assert db.resolve_database_url() is None
