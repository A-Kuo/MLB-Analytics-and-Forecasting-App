"""Tests for macroservice/insights_db.py's leaderboard registry and query.

Mocks the SQLAlchemy Engine/Connection, matching tests/test_season_stats_db.py's
pattern. See tests/test_insights_db_integration.py for the opt-in
real-database round-trip.
"""
from __future__ import annotations

from unittest.mock import MagicMock

from macroservice import insights_db


def _engine_returning_rows(rows: list[dict]):
    engine = MagicMock()
    conn = engine.connect.return_value.__enter__.return_value
    conn.execute.return_value.mappings.return_value.all.return_value = rows
    return engine, conn


# ---------------------------------------------------------------------------
# is_ascending_metric -- the domain-correction from the user's own example
# ---------------------------------------------------------------------------


def test_era_is_ascending():
    assert insights_db.is_ascending_metric("era", "pitching") is True


def test_whip_is_ascending():
    assert insights_db.is_ascending_metric("whip", "pitching") is True


def test_pitcher_walks_allowed_is_ascending():
    assert insights_db.is_ascending_metric("baseOnBalls", "pitching") is True


def test_pitcher_earned_runs_is_ascending():
    assert insights_db.is_ascending_metric("earnedRuns", "pitching") is True


def test_pitcher_strikeouts_thrown_is_descending():
    # More Ks thrown is better -- distinct from walks allowed, which the
    # user's own example conflated with strikeouts.
    assert insights_db.is_ascending_metric("strikeOuts", "pitching") is False


def test_hitter_strikeouts_is_descending():
    # A hitter's own strikeout count -- most-strikeouts leaderboard, same
    # descending convention as every other hitting counting stat. Distinct
    # registry entry from the pitcher's "strikeOuts" above (same key,
    # different group, different table).
    assert insights_db.is_ascending_metric("strikeOuts", "hitting") is False


def test_hitter_walks_is_descending():
    # A hitter's own walks (baseOnBalls) is a counting stat where more is
    # better -- distinct from a pitcher's walks *allowed*, same key,
    # opposite direction, resolved by the ``group`` parameter.
    assert insights_db.is_ascending_metric("baseOnBalls", "hitting") is False


def test_every_hitting_rate_and_counting_stat_is_descending():
    for key in ("avg", "obp", "slg", "ops", "homeRuns", "rbi", "xba", "avgExitVelocity", "hardHitPct", "barrelPct"):
        assert insights_db.is_ascending_metric(key, "hitting") is False


def test_every_pitching_statcast_metric_is_descending():
    for key in ("cswPct", "whiffPct", "chasePct", "avgVelocity", "inningsPitched"):
        assert insights_db.is_ascending_metric(key, "pitching") is False


# ---------------------------------------------------------------------------
# top_players_by_metric
# ---------------------------------------------------------------------------


def test_top_players_by_metric_maps_rows_to_dicts():
    rows = [{"player_id": 1, "name": "A", "debut_year": 2010, "last_active_year": None, "active": True, "metric_value": 0.3}]
    engine, _ = _engine_returning_rows(rows)
    result = insights_db.top_players_by_metric(engine, "avg", "hitting", 2023, frozenset({147}))
    assert result == rows


def test_top_players_by_metric_passes_team_ids_as_a_list_not_a_frozenset():
    engine, conn = _engine_returning_rows([])
    insights_db.top_players_by_metric(engine, "avg", "hitting", 2023, frozenset({147, 111}), limit=5)
    _, params = conn.execute.call_args[0]
    assert isinstance(params["team_ids"], list)
    assert set(params["team_ids"]) == {147, 111}
    assert params["season"] == 2023
    assert params["limit"] == 5


def test_top_players_by_metric_uses_ascending_order_for_era():
    engine, conn = _engine_returning_rows([])
    insights_db.top_players_by_metric(engine, "era", "pitching", 2023, frozenset({147}))
    sql, _ = conn.execute.call_args[0]
    assert "ASC" in str(sql)


def test_top_players_by_metric_uses_descending_order_for_home_runs():
    engine, conn = _engine_returning_rows([])
    insights_db.top_players_by_metric(engine, "homeRuns", "hitting", 2023, frozenset({147}))
    sql, _ = conn.execute.call_args[0]
    assert "DESC" in str(sql)


def test_top_players_by_metric_selects_from_the_registered_view_and_column():
    # Queries v_insights_hitting (db/views/), not player_statcast_hitting_
    # season directly -- the view already joins that table in along with
    # player_season_team/players, so this lookup needs no JOIN of its own.
    engine, conn = _engine_returning_rows([])
    insights_db.top_players_by_metric(engine, "xba", "hitting", 2023, frozenset({147}))
    sql, _ = conn.execute.call_args[0]
    assert "v_insights_hitting" in str(sql)
    assert "xba" in str(sql)


# ---------------------------------------------------------------------------
# upsert_player_season_team
# ---------------------------------------------------------------------------


def test_upsert_player_season_team_is_a_noop_for_empty_rows():
    engine = MagicMock()
    insights_db.upsert_player_season_team(engine, [])
    engine.begin.assert_not_called()


def test_upsert_player_season_team_executes_with_given_rows():
    engine = MagicMock()
    conn = engine.begin.return_value.__enter__.return_value
    rows = [{"player_id": 1, "team_id": 147, "season": 2023, "position": "SS", "is_pitcher": False}]
    insights_db.upsert_player_season_team(engine, rows)
    _, params = conn.execute.call_args[0]
    assert params == rows
