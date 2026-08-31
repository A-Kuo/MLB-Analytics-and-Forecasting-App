"""Generic Postgres connection/schema utilities, shared by every domain
that caches data in the app's Neon instance (roster history, PyTorch
team-forecast results, season stats).

Deliberately Streamlit-free -- callers supply an already-open SQLAlchemy
Engine (from st.connection in client.py, or a plain create_engine in a
standalone script), so this stays importable without Streamlit installed,
which macroservice/api.py's standalone FastAPI mode depends on.
"""
from __future__ import annotations

import os
import tomllib
from pathlib import Path

from psycopg.rows import dict_row

from sqlalchemy import Engine, text

_REPO_ROOT = Path(__file__).parent.parent
SCHEMA_PATH = _REPO_ROOT / "db" / "schema.sql"
SECRETS_PATH = _REPO_ROOT / ".streamlit" / "secrets.toml"


def normalize_database_url(url: str) -> str:
    """Points a Postgres URL at the psycopg3 driver this project installs.

    Neon (and most providers) hand out a bare ``postgresql://`` string, but
    SQLAlchemy maps that to psycopg2, which isn't a dependency here -- the
    result is a confusing ModuleNotFoundError at connect time. Rewriting the
    scheme means the connection string can be pasted verbatim from the Neon
    dashboard into any of the places that need it, rather than each one
    silently requiring a hand-edit.

    Also accepts a full ``[connections.postgresql]`` TOML block, since the
    same credential is configured in both shapes (TOML for Streamlit's
    secrets, bare URL for the backfill script's DATABASE_URL) and pasting
    the wrong one into the wrong place is an easy mistake to make. The
    monthly backfill silently going stale is a worse outcome than being
    lenient about which form arrives.
    """
    url = url.strip()
    if url.startswith("["):
        try:
            parsed = tomllib.loads(url).get("connections", {}).get("postgresql", {}).get("url")
        except tomllib.TOMLDecodeError:
            parsed = None
        if parsed:
            url = parsed.strip()
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix) :]
    return url


def resolve_database_url() -> str | None:
    """The connection string for non-Streamlit callers (backfill/loader
    scripts, integration tests), normalized for psycopg3.

    Prefers DATABASE_URL -- the only thing available in CI -- but falls back
    to the local .streamlit/secrets.toml so a developer who already
    configured the app doesn't have to keep the same credential in two
    places just to run a script by hand. Returns None when neither is
    usable, leaving it to callers to decide whether that's fatal.
    """
    env_url = os.environ.get("DATABASE_URL")
    if env_url:
        return normalize_database_url(env_url)
    if SECRETS_PATH.is_file():
        try:
            secrets = tomllib.loads(SECRETS_PATH.read_text())
        except tomllib.TOMLDecodeError:
            return None
        url = secrets.get("connections", {}).get("postgresql", {}).get("url")
        if url:
            return normalize_database_url(url)
    return None


def ensure_schema(engine: Engine) -> None:
    """Applies db/schema.sql. Idempotent (CREATE TABLE IF NOT EXISTS), so
    it's safe to call on every backfill/load run, regardless of which
    domain's script is calling it -- the file is the single source of
    truth for every table across every domain.
    """
    with engine.begin() as conn:
        conn.execute(text(SCHEMA_PATH.read_text()))
