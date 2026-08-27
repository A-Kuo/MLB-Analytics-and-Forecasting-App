"""Real-Postgres round-trip for macroservice/insights_db.py.

Skipped unless DATABASE_URL is set (or a local .streamlit/secrets.toml
exists), mirroring tests/test_season_stats_db_integration.py's rationale.

Uses player/team ids far outside any real MLB id range so they can't
collide with cached data for an actual player/team, and cleans up after
itself.
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text

from macroservice import db, insights_db

DATABASE_URL = db.resolve_database_url()

pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="requires DATABASE_URL or a local .streamlit/secrets.toml"
)

SEASON = 1901  # far outside any season a real backfill would touch
TEAM_A = 999_201
TEAM_B = 999_202
PLAYER_HIGH = 999_000_201  # higher AVG
PLAYER_LOW = 999_000_202  # lower AVG
PLAYER_TRADED = 999_000_203  # rostered on both TEAM_A and TEAM_B this season


@pytest.fixture
def engine():
    eng = create_engine(DATABASE_URL)
    db.ensure_schema(eng)
    player_ids = (PLAYER_HIGH, PLAYER_LOW, PLAYER_TRADED)
    with eng.begin() as conn:
        for player_id in player_ids:
            conn.execute(
                text(
                    "INSERT INTO players (id, name, debut_year, last_active_year, active) "
                    "VALUES (:id, :name, 2015, 2020, false) "
                    "ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name"
                ),
                {"id": player_id, "name": f"Test Player {player_id}"},
            )
    yield eng
    with eng.begin() as conn:
        for table in ("player_season_hitting_stats", "player_season_pitching_stats", "player_season_team"):
            for player_id in player_ids:
                conn.execute(text(f"DELETE FROM {table} WHERE player_id = :p"), {"p": player_id})
        for player_id in player_ids:
            conn.execute(text("DELETE FROM players WHERE id = :p"), {"p": player_id})
    eng.dispose()


def _upsert_hitting_avg(engine, player_id: int, avg: float) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO player_season_hitting_stats (player_id, season, avg) "
                "VALUES (:player_id, :season, :avg) "
                "ON CONFLICT (player_id, season) DO UPDATE SET avg = EXCLUDED.avg"
            ),
            {"player_id": player_id, "season": SEASON, "avg": avg},
        )


def test_top_players_by_metric_ranks_descending_for_avg(engine):
    _upsert_hitting_avg(engine, PLAYER_HIGH, 0.350)
    _upsert_hitting_avg(engine, PLAYER_LOW, 0.220)
    insights_db.upsert_player_season_team(
        engine,
        [
            {"player_id": PLAYER_HIGH, "team_id": TEAM_A, "season": SEASON, "position": "SS", "is_pitcher": False},
            {"player_id": PLAYER_LOW, "team_id": TEAM_A, "season": SEASON, "position": "2B", "is_pitcher": False},
        ],
    )
    rows = insights_db.top_players_by_metric(engine, "avg", "hitting", SEASON, frozenset({TEAM_A}))
    assert [r["player_id"] for r in rows] == [PLAYER_HIGH, PLAYER_LOW]


def test_top_players_by_metric_ranks_ascending_for_era(engine):
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO player_season_pitching_stats (player_id, season, era) "
                "VALUES (:player_id, :season, :era) "
                "ON CONFLICT (player_id, season) DO UPDATE SET era = EXCLUDED.era"
            ),
            {"player_id": PLAYER_HIGH, "season": SEASON, "era": 2.10},
        )
        conn.execute(
            text(
                "INSERT INTO player_season_pitching_stats (player_id, season, era) "
                "VALUES (:player_id, :season, :era) "
                "ON CONFLICT (player_id, season) DO UPDATE SET era = EXCLUDED.era"
            ),
            {"player_id": PLAYER_LOW, "season": SEASON, "era": 5.40},
        )
    insights_db.upsert_player_season_team(
        engine,
        [
            {"player_id": PLAYER_HIGH, "team_id": TEAM_A, "season": SEASON, "position": "P", "is_pitcher": True},
            {"player_id": PLAYER_LOW, "team_id": TEAM_A, "season": SEASON, "position": "P", "is_pitcher": True},
        ],
    )
    rows = insights_db.top_players_by_metric(engine, "era", "pitching", SEASON, frozenset({TEAM_A}))
    assert [r["player_id"] for r in rows] == [PLAYER_HIGH, PLAYER_LOW]  # lowest ERA first


def test_player_rostered_under_two_selected_teams_appears_once(engine):
    _upsert_hitting_avg(engine, PLAYER_TRADED, 0.300)
    insights_db.upsert_player_season_team(
        engine,
        [
            {"player_id": PLAYER_TRADED, "team_id": TEAM_A, "season": SEASON, "position": "SS", "is_pitcher": False},
            {"player_id": PLAYER_TRADED, "team_id": TEAM_B, "season": SEASON, "position": "SS", "is_pitcher": False},
        ],
    )
    rows = insights_db.top_players_by_metric(engine, "avg", "hitting", SEASON, frozenset({TEAM_A, TEAM_B}))
    player_ids = [r["player_id"] for r in rows]
    assert player_ids.count(PLAYER_TRADED) == 1
