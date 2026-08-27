"""Real-Postgres round-trip for macroservice/season_stats_db.py.

Skipped unless DATABASE_URL is set (or a local .streamlit/secrets.toml
exists), so the default suite stays hermetic. Mirrors
tests/test_roster_history_db_integration.py's rationale: this covers what
the mocked tests structurally can't (ON CONFLICT semantics, the psycopg3
dialect actually accepting these statements).

Uses ids far outside any real MLB id range so they can't collide with
cached data for an actual player/team, and cleans up after itself.
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text

from macroservice import db, season_stats_db

DATABASE_URL = db.resolve_database_url()

pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="requires DATABASE_URL or a local .streamlit/secrets.toml"
)

TEST_PLAYER_ID = 999_000_101
TEST_TEAM_ID = 999_101


@pytest.fixture
def engine():
    eng = create_engine(DATABASE_URL)
    db.ensure_schema(eng)
    yield eng
    with eng.begin() as conn:
        for table in (
            "player_season_hitting_stats", "player_season_pitching_stats",
            "player_statcast_hitting_season", "player_statcast_pitching_season",
            "player_game_log_hitting", "player_game_log_pitching",
        ):
            conn.execute(text(f"DELETE FROM {table} WHERE player_id = :p"), {"p": TEST_PLAYER_ID})
        for table in ("team_season_hitting_stats", "team_season_pitching_stats"):
            conn.execute(text(f"DELETE FROM {table} WHERE team_id = :t"), {"t": TEST_TEAM_ID})
    eng.dispose()


def test_player_season_hitting_round_trip(engine):
    season_stats_db.upsert_player_season_hitting(
        engine, TEST_PLAYER_ID, 2023, {"avg": ".300", "obp": ".400", "slg": ".500", "ops": ".900",
                                        "homeRuns": 30, "rbi": 90, "strikeOuts": 120, "baseOnBalls": 60}
    )
    result = season_stats_db.fetch_player_season_hitting(engine, TEST_PLAYER_ID, 2023)
    assert result == {"avg": 0.3, "obp": 0.4, "slg": 0.5, "ops": 0.9, "homeRuns": 30, "rbi": 90, "strikeOuts": 120, "baseOnBalls": 60}


def test_player_season_hitting_upsert_overwrites_in_place(engine):
    season_stats_db.upsert_player_season_hitting(engine, TEST_PLAYER_ID, 2023, {"avg": ".300"})
    season_stats_db.upsert_player_season_hitting(engine, TEST_PLAYER_ID, 2023, {"avg": ".333"})
    result = season_stats_db.fetch_player_season_hitting(engine, TEST_PLAYER_ID, 2023)
    assert result["avg"] == 0.333


def test_player_season_hitting_empty_result_is_a_real_cache_hit(engine):
    # Confirms the "confirmed empty" contract: a real API {} result still
    # reads back as a non-None dict (all fields None), distinguishable
    # from a genuine miss.
    season_stats_db.upsert_player_season_hitting(engine, TEST_PLAYER_ID, 2023, {})
    result = season_stats_db.fetch_player_season_hitting(engine, TEST_PLAYER_ID, 2023)
    assert result is not None
    assert result["avg"] is None


def test_player_season_hitting_fetch_returns_none_for_unwritten_season(engine):
    assert season_stats_db.fetch_player_season_hitting(engine, TEST_PLAYER_ID, 1901) is None


def test_player_season_pitching_round_trip(engine):
    season_stats_db.upsert_player_season_pitching(
        engine, TEST_PLAYER_ID, 2023, {"era": "3.50", "whip": "1.10", "strikeOuts": 200,
                                        "baseOnBalls": 50, "inningsPitched": "182.1", "earnedRuns": 70}
    )
    result = season_stats_db.fetch_player_season_pitching(engine, TEST_PLAYER_ID, 2023)
    assert result["era"] == 3.5
    assert result["inningsPitched"] == 182.1


def test_player_statcast_hitting_season_round_trip(engine):
    season_stats_db.upsert_player_statcast_hitting_season(
        engine, TEST_PLAYER_ID, 2023, {"xba": 0.28, "avgExitVelocity": 91.2, "hardHitPct": 0.45, "barrelPct": 0.09}
    )
    result = season_stats_db.fetch_player_statcast_hitting_season(engine, TEST_PLAYER_ID, 2023)
    assert result == {"xba": 0.28, "avgExitVelocity": 91.2, "hardHitPct": 0.45, "barrelPct": 0.09}


def test_player_statcast_pitching_season_round_trip(engine):
    season_stats_db.upsert_player_statcast_pitching_season(
        engine, TEST_PLAYER_ID, 2023, {"cswPct": 0.3, "whiffPct": 0.25, "chasePct": 0.28, "avgVelocity": 94.1}
    )
    result = season_stats_db.fetch_player_statcast_pitching_season(engine, TEST_PLAYER_ID, 2023)
    assert result == {"cswPct": 0.3, "whiffPct": 0.25, "chasePct": 0.28, "avgVelocity": 94.1}


def test_player_game_log_hitting_round_trip_and_doubleheader(engine):
    splits = [
        {"date": "2023-04-05", "opponent": {"name": "PHI"}, "stat": {"atBats": 3, "hits": 1, "avg": ".333"}},
        {"date": "2023-04-05", "opponent": {"name": "PHI"}, "stat": {"atBats": 4, "hits": 2, "avg": ".500"}},
    ]
    season_stats_db.upsert_player_game_log_hitting(engine, TEST_PLAYER_ID, 2023, splits)
    result = season_stats_db.fetch_player_game_log_hitting(engine, TEST_PLAYER_ID, 2023)
    assert len(result) == 2  # both doubleheader games persisted, not overwritten

    # Re-upserting the same splits must update in place, not duplicate.
    season_stats_db.upsert_player_game_log_hitting(engine, TEST_PLAYER_ID, 2023, splits)
    result_again = season_stats_db.fetch_player_game_log_hitting(engine, TEST_PLAYER_ID, 2023)
    assert len(result_again) == 2


def test_player_game_log_pitching_round_trip(engine):
    splits = [{"date": "2023-04-05", "opponent": {"name": "PHI"},
               "stat": {"inningsPitched": "6.2", "hits": 5, "earnedRuns": 2, "strikeOuts": 7, "baseOnBalls": 1, "era": "2.70"}}]
    season_stats_db.upsert_player_game_log_pitching(engine, TEST_PLAYER_ID, 2023, splits)
    result = season_stats_db.fetch_player_game_log_pitching(engine, TEST_PLAYER_ID, 2023)
    assert len(result) == 1
    assert result[0]["stat"]["inningsPitched"] == 6.2


def test_team_season_hitting_round_trip(engine):
    season_stats_db.upsert_team_season_hitting(
        engine, TEST_TEAM_ID, 2023, {"runs": 700, "avg": ".250", "obp": ".320", "slg": ".420", "ops": ".740", "gamesPlayed": 162}
    )
    result = season_stats_db.fetch_team_season_hitting(engine, TEST_TEAM_ID, 2023)
    assert result["runs"] == 700
    assert result["gamesPlayed"] == 162


def test_team_season_pitching_round_trip(engine):
    season_stats_db.upsert_team_season_pitching(
        engine, TEST_TEAM_ID, 2023, {"wins": 82, "losses": 80, "runs": 698, "era": "3.97", "whip": "1.24", "gamesPlayed": 162}
    )
    result = season_stats_db.fetch_team_season_pitching(engine, TEST_TEAM_ID, 2023)
    assert result["runs"] == 698  # runs_allowed column, exposed back as "runs" to match live API shape
    assert result["wins"] == 82
