"""Tests for macroservice/season_stats_db.py.

Mocks the SQLAlchemy Engine/Connection, matching tests/test_roster_history_db.py's
pattern. See tests/test_season_stats_db_integration.py for the opt-in
real-database round-trip.
"""
from __future__ import annotations

from unittest.mock import MagicMock

from macroservice import season_stats_db


def _engine_returning_row(row: dict | None):
    engine = MagicMock()
    conn = engine.connect.return_value.__enter__.return_value
    conn.execute.return_value.mappings.return_value.first.return_value = row
    return engine, conn


def _engine_returning_rows(rows: list[dict]):
    engine = MagicMock()
    conn = engine.connect.return_value.__enter__.return_value
    conn.execute.return_value.mappings.return_value.all.return_value = rows
    return engine, conn


def _writable_engine():
    engine = MagicMock()
    conn = engine.begin.return_value.__enter__.return_value
    return engine, conn


# ---------------------------------------------------------------------------
# player season hitting/pitching stats
# ---------------------------------------------------------------------------


def test_fetch_player_season_hitting_returns_none_on_miss():
    engine, _ = _engine_returning_row(None)
    assert season_stats_db.fetch_player_season_hitting(engine, 660271, 2023) is None


def test_fetch_player_season_hitting_maps_columns_to_api_key_names():
    row = {"avg": 0.3, "obp": 0.4, "slg": 0.5, "ops": 0.9, "home_runs": 30, "rbi": 90, "strikeouts": 120, "walks": 60}
    engine, _ = _engine_returning_row(row)
    result = season_stats_db.fetch_player_season_hitting(engine, 660271, 2023)
    assert result == {"avg": 0.3, "obp": 0.4, "slg": 0.5, "ops": 0.9, "homeRuns": 30, "rbi": 90, "strikeOuts": 120, "baseOnBalls": 60}


def test_fetch_player_season_hitting_filters_by_player_and_season():
    engine, conn = _engine_returning_row(None)
    season_stats_db.fetch_player_season_hitting(engine, 660271, 2023)
    sql, params = conn.execute.call_args[0]
    assert params == {"player_id": 660271, "season": 2023}
    assert "player_id = :player_id AND season = :season" in str(sql)


def test_upsert_player_season_hitting_casts_and_upserts():
    engine, conn = _writable_engine()
    season_stats_db.upsert_player_season_hitting(engine, 660271, 2023, {"avg": ".312", "homeRuns": "31", "obp": None})
    sql, params = conn.execute.call_args[0]
    assert "ON CONFLICT (player_id, season) DO UPDATE" in str(sql)
    assert params["avg"] == 0.312
    assert params["home_runs"] == 31
    assert params["obp"] is None


def test_upsert_player_season_hitting_writes_a_row_for_an_empty_result():
    # A real "no data" API response ({}) still gets cached -- distinguishes
    # "checked, nothing there" from "never checked" on the next read.
    engine, conn = _writable_engine()
    season_stats_db.upsert_player_season_hitting(engine, 660271, 2023, {})
    engine.begin.assert_called_once()
    params = conn.execute.call_args[0][1]
    assert params["player_id"] == 660271
    assert params["avg"] is None


def test_fetch_player_season_pitching_maps_columns_to_api_key_names():
    row = {"era": 3.5, "whip": 1.1, "strikeouts": 200, "walks": 50, "innings_pitched": 180.1, "earned_runs": 70}
    engine, _ = _engine_returning_row(row)
    result = season_stats_db.fetch_player_season_pitching(engine, 543037, 2023)
    assert result == {"era": 3.5, "whip": 1.1, "strikeOuts": 200, "baseOnBalls": 50, "inningsPitched": 180.1, "earnedRuns": 70}


def test_upsert_player_season_pitching_preserves_thirds_notation_as_naive_float():
    # "182.1" (thirds notation, 182 and 1/3 innings) is stored exactly as
    # the live path already parses it (float(raw)) -- not "fixed" here.
    engine, conn = _writable_engine()
    season_stats_db.upsert_player_season_pitching(engine, 543037, 2023, {"inningsPitched": "182.1"})
    params = conn.execute.call_args[0][1]
    assert params["innings_pitched"] == 182.1


# ---------------------------------------------------------------------------
# player Statcast season aggregates
# ---------------------------------------------------------------------------


def test_fetch_player_statcast_hitting_season_maps_columns():
    row = {"xba": 0.28, "avg_exit_velocity": 91.2, "hard_hit_pct": 0.45, "barrel_pct": 0.09}
    engine, _ = _engine_returning_row(row)
    result = season_stats_db.fetch_player_statcast_hitting_season(engine, 660271, 2023)
    assert result == {"xba": 0.28, "avgExitVelocity": 91.2, "hardHitPct": 0.45, "barrelPct": 0.09}


def test_fetch_player_statcast_hitting_season_returns_none_on_miss():
    engine, _ = _engine_returning_row(None)
    assert season_stats_db.fetch_player_statcast_hitting_season(engine, 660271, 2023) is None


def test_upsert_player_statcast_pitching_season_casts_values():
    engine, conn = _writable_engine()
    season_stats_db.upsert_player_statcast_pitching_season(
        engine, 543037, 2023, {"cswPct": 0.3, "whiffPct": 0.25, "chasePct": None, "avgVelocity": 94.1}
    )
    params = conn.execute.call_args[0][1]
    assert params["csw_pct"] == 0.3
    assert params["chase_pct"] is None


# ---------------------------------------------------------------------------
# player game logs
# ---------------------------------------------------------------------------


def test_fetch_player_game_log_hitting_reconstructs_split_shape():
    row = {"game_date": "2023-04-05", "opponent": "PHI", "at_bats": 4, "hits": 2, "home_runs": 1,
           "rbi": 3, "walks": 1, "strikeouts": 0, "avg": 0.5}
    engine, _ = _engine_returning_rows([row])
    result = season_stats_db.fetch_player_game_log_hitting(engine, 660271, 2023)
    assert result == [{"date": "2023-04-05", "opponent": {"name": "PHI"},
                        "stat": {"atBats": 4, "hits": 2, "homeRuns": 1, "rbi": 3, "baseOnBalls": 1, "strikeOuts": 0, "avg": 0.5}}]


def test_fetch_player_game_log_hitting_returns_empty_list_for_miss_or_confirmed_empty():
    engine, _ = _engine_returning_rows([])
    assert season_stats_db.fetch_player_game_log_hitting(engine, 660271, 2023) == []


def test_upsert_player_game_log_hitting_assigns_game_index_for_doubleheader():
    splits = [
        {"date": "2023-04-05", "opponent": {"name": "PHI"}, "stat": {"atBats": 3, "hits": 1}},
        {"date": "2023-04-05", "opponent": {"name": "PHI"}, "stat": {"atBats": 4, "hits": 2}},  # nightcap
        {"date": "2023-04-06", "opponent": {"name": "PHI"}, "stat": {"atBats": 4, "hits": 0}},
    ]
    engine, conn = _writable_engine()
    season_stats_db.upsert_player_game_log_hitting(engine, 660271, 2023, splits)
    params = conn.execute.call_args[0][1]
    indices_by_date = {}
    for p in params:
        indices_by_date.setdefault(p["game_date"], []).append(p["game_index"])
    assert sorted(indices_by_date["2023-04-05"]) == [0, 1]
    assert indices_by_date["2023-04-06"] == [0]


def test_upsert_player_game_log_hitting_empty_splits_is_a_noop():
    engine, conn = _writable_engine()
    season_stats_db.upsert_player_game_log_hitting(engine, 660271, 2023, [])
    engine.begin.assert_not_called()


def test_upsert_player_game_log_pitching_maps_fields():
    splits = [{"date": "2023-04-05", "opponent": {"name": "PHI"},
               "stat": {"inningsPitched": "6.2", "hits": 5, "earnedRuns": 2, "strikeOuts": 7, "baseOnBalls": 1, "era": "2.70"}}]
    engine, conn = _writable_engine()
    season_stats_db.upsert_player_game_log_pitching(engine, 543037, 2023, splits)
    params = conn.execute.call_args[0][1][0]
    assert params["innings_pitched"] == 6.2
    assert params["era"] == 2.70
    assert params["game_index"] == 0


# ---------------------------------------------------------------------------
# team season stats
# ---------------------------------------------------------------------------


def test_fetch_team_season_hitting_maps_columns():
    row = {"runs": 700, "avg": 0.25, "obp": 0.32, "slg": 0.42, "ops": 0.74, "games_played": 162}
    engine, _ = _engine_returning_row(row)
    result = season_stats_db.fetch_team_season_hitting(engine, 147, 2023)
    assert result == {"runs": 700, "avg": 0.25, "obp": 0.32, "slg": 0.42, "ops": 0.74, "gamesPlayed": 162}


def test_fetch_team_season_pitching_maps_runs_allowed_to_runs_key():
    # The live API's pitching-group "runs" field means runs given up --
    # the cache mirrors that naming so callers see an identical shape.
    row = {"wins": 82, "losses": 80, "runs_allowed": 698, "era": 3.97, "whip": 1.24, "games_played": 162}
    engine, _ = _engine_returning_row(row)
    result = season_stats_db.fetch_team_season_pitching(engine, 147, 2023)
    assert result == {"wins": 82, "losses": 80, "runs": 698, "era": 3.97, "whip": 1.24, "gamesPlayed": 162}


def test_upsert_team_season_pitching_maps_runs_key_to_runs_allowed_column():
    engine, conn = _writable_engine()
    season_stats_db.upsert_team_season_pitching(engine, 147, 2023, {"runs": 698, "wins": 82})
    params = conn.execute.call_args[0][1]
    assert params["runs_allowed"] == 698
    assert params["wins"] == 82


def test_upsert_team_season_hitting_upsert_key_matches_pk():
    engine, conn = _writable_engine()
    season_stats_db.upsert_team_season_hitting(engine, 147, 2023, {"runs": 700})
    sql = str(conn.execute.call_args[0][0])
    assert "ON CONFLICT (team_id, season) DO UPDATE" in sql
