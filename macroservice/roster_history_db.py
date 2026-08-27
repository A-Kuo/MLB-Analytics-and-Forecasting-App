"""Postgres-backed storage for all-time roster / player-bio data.

A durable cache in front of macroservice/roster_history.py's live MLB Stats
API calls: the position checkboxes in app.py resolve rosters on every
render, and the in-process TTLCache backing the API path (macroservice/
caching.py) is wiped whenever the Streamlit process restarts or sleeps.

Deliberately Streamlit-free -- every function takes an already-open
SQLAlchemy Engine, so the same code serves both the Streamlit app (which
supplies an engine from st.connection, see client.py) and the standalone
backfill script (scripts/backfill_roster_history.py, a plain create_engine).
That also keeps macroservice/ importable without Streamlit installed, which
macroservice/api.py's standalone FastAPI mode depends on.

This module stores and returns *raw* bio/stint rows only. Interpreting them
-- most notably deciding whether a missing last_active_year means "still
playing" or "data gap" -- stays in roster_history._active_year_ranges, so
that rule lives in exactly one place rather than being duplicated in SQL.

Connection/schema utilities (normalize_database_url, resolve_database_url,
ensure_schema, SCHEMA_PATH, SECRETS_PATH) live in macroservice/db.py --
they're generic across every domain that caches data in this Neon
instance, not roster-specific. Import them from there.
"""
from __future__ import annotations

from sqlalchemy import Engine, text

_FETCH_SQL = text(
    """
    SELECT p.id, p.name, p.debut_year, p.last_active_year, p.active,
           rs.positions, rs.is_pitcher
    FROM roster_stints rs
    JOIN players p ON p.id = rs.player_id
    WHERE rs.team_id = :team_id
    """
)

_UPSERT_PLAYER_SQL = text(
    """
    INSERT INTO players (id, name, debut_year, last_active_year, active)
    VALUES (:id, :name, :debut_year, :last_active_year, :active)
    ON CONFLICT (id) DO UPDATE SET
        name = EXCLUDED.name,
        debut_year = EXCLUDED.debut_year,
        last_active_year = EXCLUDED.last_active_year,
        active = EXCLUDED.active
    """
)

_UPSERT_STINT_SQL = text(
    """
    INSERT INTO roster_stints (team_id, player_id, positions, is_pitcher)
    VALUES (:team_id, :player_id, :positions, :is_pitcher)
    ON CONFLICT (team_id, player_id) DO UPDATE SET
        positions = EXCLUDED.positions,
        is_pitcher = EXCLUDED.is_pitcher
    """
)


def fetch_team_roster_rows(engine: Engine, team_id: int) -> list[dict]:
    """Raw (unenriched) bio+stint rows for one team, in the same shape
    roster_history.enrich_with_active_years expects.

    Returns [] when this team has no rows yet -- callers treat that as a
    cache miss and fall back to the live API (see client.py), rather than
    it being an error worth raising.
    """
    with engine.connect() as conn:
        rows = conn.execute(_FETCH_SQL, {"team_id": team_id}).mappings().all()
    return [{**row, "positions": list(row["positions"])} for row in rows]


def upsert_team_roster(engine: Engine, team_id: int, roster: list[dict]) -> None:
    """Writes one team's roster, replacing whatever was there for those
    players. Takes the enriched shape from
    roster_history.get_team_roster_with_active_years -- the computed
    active_year_ranges/active_years_label keys are ignored, since they're
    derived on read rather than stored.

    One transaction for the whole team: a partially-written roster would
    read back as a complete (but wrong) cache hit, so it's all or nothing.
    """
    if not roster:
        return
    player_params = [
        {
            "id": entry["id"],
            "name": entry["name"],
            "debut_year": entry["debut_year"],
            "last_active_year": entry["last_active_year"],
            "active": entry["active"],
        }
        for entry in roster
    ]
    stint_params = [
        {
            "team_id": team_id,
            "player_id": entry["id"],
            "positions": entry["positions"],
            "is_pitcher": entry["is_pitcher"],
        }
        for entry in roster
    ]
    with engine.begin() as conn:
        # players first: roster_stints.player_id references it.
        conn.execute(_UPSERT_PLAYER_SQL, player_params)
        conn.execute(_UPSERT_STINT_SQL, stint_params)
