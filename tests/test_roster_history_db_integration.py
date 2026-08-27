"""Real-Postgres round-trip for the roster-history cache.

Skipped unless DATABASE_URL is set, so the default suite stays hermetic:

    DATABASE_URL=postgresql+psycopg://... python -m pytest tests/test_roster_history_db_integration.py

This covers what the mocked tests structurally can't -- text[] column
round-tripping, ON CONFLICT ... DO UPDATE semantics, and the psycopg3
dialect actually accepting these statements. SQLite is deliberately not
used as a stand-in: it has no array type and different upsert constructs,
so a passing SQLite run would prove nothing about the Postgres path.

Uses a team_id far outside the real 108-158 range so it can't collide with
cached data for an actual team, and cleans up after itself.
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text

from macroservice import db, roster_history, roster_history_db

DATABASE_URL = db.resolve_database_url()

pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="requires DATABASE_URL or a local .streamlit/secrets.toml"
)

TEST_TEAM_ID = 999_001

_ROSTER = [
    {
        "id": 999_000_001,
        "name": "Integration Shortstop",
        "positions": ["SS"],
        "is_pitcher": False,
        "debut_year": 2015,
        "last_active_year": None,
        "active": True,
    },
    {
        "id": 999_000_002,
        "name": "Integration Outfielder",
        "positions": ["LF", "CF", "RF"],
        "is_pitcher": False,
        "debut_year": 1890,
        "last_active_year": None,
        "active": False,  # the retired-with-a-data-gap case
    },
]


@pytest.fixture
def engine():
    eng = create_engine(DATABASE_URL)
    db.ensure_schema(eng)
    yield eng
    with eng.begin() as conn:
        conn.execute(text("DELETE FROM roster_stints WHERE team_id = :t"), {"t": TEST_TEAM_ID})
        conn.execute(
            text("DELETE FROM players WHERE id = ANY(:ids)"), {"ids": [e["id"] for e in _ROSTER]}
        )
    eng.dispose()


def test_ensure_schema_is_idempotent(engine):
    db.ensure_schema(engine)  # second call must not raise


def test_upsert_then_fetch_round_trip(engine):
    roster_history_db.upsert_team_roster(engine, TEST_TEAM_ID, _ROSTER)
    rows = roster_history_db.fetch_team_roster_rows(engine, TEST_TEAM_ID)
    by_id = {row["id"]: row for row in rows}
    assert set(by_id) == {999_000_001, 999_000_002}
    assert by_id[999_000_001]["positions"] == ["SS"]
    assert by_id[999_000_002]["positions"] == ["LF", "CF", "RF"]
    assert by_id[999_000_001]["active"] is True
    assert by_id[999_000_002]["last_active_year"] is None


def test_fetched_rows_enrich_with_the_corrected_active_year_logic(engine):
    # The whole point of storing raw rows: the "immortal player" fix still
    # applies on read, so a retired player with no last_active_year gets a
    # single-season span rather than one running to the present.
    roster_history_db.upsert_team_roster(engine, TEST_TEAM_ID, _ROSTER)
    rows = roster_history_db.fetch_team_roster_rows(engine, TEST_TEAM_ID)
    enriched = {row["id"]: row for row in roster_history.enrich_with_active_years(rows)}
    assert enriched[999_000_001]["active_year_ranges"] == [(2015, None)]
    assert enriched[999_000_002]["active_year_ranges"] == [(1890, 1890)]
    assert roster_history.resolve_from_roster(list(enriched.values()), 2020, 2026) == {999_000_001}


def test_upsert_is_idempotent_and_updates_in_place(engine):
    roster_history_db.upsert_team_roster(engine, TEST_TEAM_ID, _ROSTER)
    changed = [{**_ROSTER[0], "name": "Renamed Shortstop", "positions": ["2B"]}, _ROSTER[1]]
    roster_history_db.upsert_team_roster(engine, TEST_TEAM_ID, changed)
    rows = roster_history_db.fetch_team_roster_rows(engine, TEST_TEAM_ID)
    assert len(rows) == 2  # updated in place, not duplicated
    updated = next(row for row in rows if row["id"] == 999_000_001)
    assert updated["name"] == "Renamed Shortstop"
    assert updated["positions"] == ["2B"]


def test_fetch_returns_empty_for_an_unknown_team(engine):
    assert roster_history_db.fetch_team_roster_rows(engine, TEST_TEAM_ID + 1) == []
