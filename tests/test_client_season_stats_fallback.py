"""Tests for client.py's Postgres-first / live-API-fallback season-stats
paths (get_season_stats, get_team_season_stats, get_game_log_splits,
_get_statcast_season).

Mirrors tests/test_client_roster_fallback.py function-for-function: DB hit
skips the live API; empty/missing DB result falls back to the API and
self-heals; a DB read error falls back to the API; an upsert error still
serves the live result; a missing/broken st.connection config falls back
to the API. Plus one case unique to this migration: a current-season
request never touches the DB layer at all.

Exercises the undecorated functions (``__wrapped__``) so Streamlit's cache
doesn't carry results between tests or need a script run context.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import client

_CURRENT_YEAR_SEASON = 9999  # always "in progress" -- never a real completed season
_PAST_SEASON = 2023  # always complete regardless of when this suite runs

_get_season_stats = client.get_season_stats.__wrapped__
_get_team_season_stats = client.get_team_season_stats.__wrapped__
_get_game_log_splits = client.get_game_log_splits.__wrapped__
_get_statcast_season = client._get_statcast_season  # not @st.cache_data-wrapped

_DB_HITTING = {"avg": 0.3, "obp": 0.4, "slg": 0.5, "ops": 0.9, "homeRuns": 30, "rbi": 90, "strikeOuts": 120, "baseOnBalls": 60}
_API_HITTING = {"avg": ".280", "obp": ".360", "slg": ".460", "ops": ".820", "homeRuns": 25, "rbi": 80, "strikeOuts": 100, "baseOnBalls": 55}


# ---------------------------------------------------------------------------
# get_season_stats
# ---------------------------------------------------------------------------


@patch("client.players.get_season_stats")
@patch("client.season_stats_db.fetch_player_season_hitting")
@patch("client._db_engine")
def test_season_stats_db_hit_skips_the_live_api(mock_engine, mock_fetch, mock_api):
    mock_fetch.return_value = _DB_HITTING
    result = _get_season_stats(660271, _PAST_SEASON, "hitting")
    mock_api.assert_not_called()
    assert result == _DB_HITTING


@patch("client.season_stats_db.upsert_player_season_hitting")
@patch("client.players.get_season_stats")
@patch("client.season_stats_db.fetch_player_season_hitting")
@patch("client._db_engine")
def test_season_stats_miss_falls_back_to_api_and_self_heals(mock_engine, mock_fetch, mock_api, mock_upsert):
    mock_fetch.return_value = None
    mock_api.return_value = _API_HITTING
    result = _get_season_stats(660271, _PAST_SEASON, "hitting")
    assert result == _API_HITTING
    mock_upsert.assert_called_once_with(mock_engine.return_value, 660271, _PAST_SEASON, _API_HITTING)


@patch("client.season_stats_db.upsert_player_season_hitting")
@patch("client.players.get_season_stats")
@patch("client.season_stats_db.fetch_player_season_hitting")
@patch("client._db_engine")
def test_season_stats_db_read_error_falls_back_to_api(mock_engine, mock_fetch, mock_api, mock_upsert):
    mock_fetch.side_effect = RuntimeError("connection refused")
    mock_api.return_value = _API_HITTING
    assert _get_season_stats(660271, _PAST_SEASON, "hitting") == _API_HITTING


@patch("client.season_stats_db.upsert_player_season_hitting")
@patch("client.players.get_season_stats")
@patch("client.season_stats_db.fetch_player_season_hitting")
@patch("client._db_engine")
def test_season_stats_upsert_error_still_serves_live_data(mock_engine, mock_fetch, mock_api, mock_upsert):
    mock_fetch.return_value = None
    mock_api.return_value = _API_HITTING
    mock_upsert.side_effect = RuntimeError("read-only transaction")
    assert _get_season_stats(660271, _PAST_SEASON, "hitting") == _API_HITTING


@patch("client.players.get_season_stats")
@patch("client.season_stats_db.fetch_player_season_hitting")
@patch("client._db_engine")
def test_season_stats_missing_secrets_config_falls_back_to_api(mock_engine, mock_fetch, mock_api):
    mock_engine.side_effect = RuntimeError("no connection named 'postgresql'")
    mock_api.return_value = _API_HITTING
    assert _get_season_stats(660271, _PAST_SEASON, "hitting") == _API_HITTING


@patch("client.players.get_season_stats")
@patch("client.season_stats_db.fetch_player_season_hitting")
@patch("client._db_engine")
def test_current_season_never_touches_the_db_layer(mock_engine, mock_fetch, mock_api):
    mock_api.return_value = _API_HITTING
    result = _get_season_stats(660271, _CURRENT_YEAR_SEASON, "hitting")
    assert result == _API_HITTING
    mock_engine.assert_not_called()
    mock_fetch.assert_not_called()


# ---------------------------------------------------------------------------
# get_team_season_stats
# ---------------------------------------------------------------------------


@patch("client.teams.get_team_season_stats")
@patch("client.season_stats_db.fetch_team_season_hitting")
@patch("client._db_engine")
def test_team_season_stats_db_hit_skips_the_live_api(mock_engine, mock_fetch, mock_api):
    mock_fetch.return_value = {"runs": 700}
    result = _get_team_season_stats(147, _PAST_SEASON, "hitting")
    mock_api.assert_not_called()
    assert result == {"runs": 700}


@patch("client.season_stats_db.upsert_team_season_hitting")
@patch("client.teams.get_team_season_stats")
@patch("client.season_stats_db.fetch_team_season_hitting")
@patch("client._db_engine")
def test_team_season_stats_miss_falls_back_and_self_heals(mock_engine, mock_fetch, mock_api, mock_upsert):
    mock_fetch.return_value = None
    mock_api.return_value = {"runs": 650}
    result = _get_team_season_stats(147, _PAST_SEASON, "hitting")
    assert result == {"runs": 650}
    mock_upsert.assert_called_once_with(mock_engine.return_value, 147, _PAST_SEASON, {"runs": 650})


@patch("client.teams.get_team_season_stats")
@patch("client.season_stats_db.fetch_team_season_hitting")
@patch("client._db_engine")
def test_team_season_stats_current_season_never_touches_db(mock_engine, mock_fetch, mock_api):
    mock_api.return_value = {"runs": 1}
    _get_team_season_stats(147, _CURRENT_YEAR_SEASON, "hitting")
    mock_engine.assert_not_called()


# ---------------------------------------------------------------------------
# get_game_log_splits
# ---------------------------------------------------------------------------


@patch("client.players.get_game_log")
@patch("client.season_stats_db.fetch_player_game_log_hitting")
@patch("client._db_engine")
def test_game_log_db_hit_skips_the_live_api(mock_engine, mock_fetch, mock_api):
    mock_fetch.return_value = [{"date": "2023-04-05"}]
    result = _get_game_log_splits(660271, _PAST_SEASON, "hitting")
    mock_api.assert_not_called()
    assert result == [{"date": "2023-04-05"}]


@patch("client.season_stats_db.upsert_player_game_log_hitting")
@patch("client.players.get_game_log")
@patch("client.season_stats_db.fetch_player_game_log_hitting")
@patch("client._db_engine")
def test_game_log_miss_falls_back_and_self_heals(mock_engine, mock_fetch, mock_api, mock_upsert):
    mock_fetch.return_value = []
    mock_api.return_value = [{"date": "2023-04-06"}]
    result = _get_game_log_splits(660271, _PAST_SEASON, "hitting")
    assert result == [{"date": "2023-04-06"}]
    mock_upsert.assert_called_once_with(mock_engine.return_value, 660271, _PAST_SEASON, [{"date": "2023-04-06"}])


@patch("client.players.get_game_log")
@patch("client.season_stats_db.fetch_player_game_log_hitting")
@patch("client._db_engine")
def test_game_log_db_read_error_falls_back_to_api(mock_engine, mock_fetch, mock_api):
    mock_fetch.side_effect = RuntimeError("connection refused")
    mock_api.return_value = [{"date": "2023-04-06"}]
    assert _get_game_log_splits(660271, _PAST_SEASON, "hitting") == [{"date": "2023-04-06"}]


@patch("client.players.get_game_log")
@patch("client.season_stats_db.fetch_player_game_log_hitting")
@patch("client._db_engine")
def test_game_log_current_season_never_touches_db(mock_engine, mock_fetch, mock_api):
    mock_api.return_value = []
    _get_game_log_splits(660271, _CURRENT_YEAR_SEASON, "hitting")
    mock_engine.assert_not_called()


# ---------------------------------------------------------------------------
# _get_statcast_season
# ---------------------------------------------------------------------------


@patch("client.statcast_season.compute_hitter_statcast_season")
@patch("client.season_stats_db.fetch_player_statcast_hitting_season")
@patch("client._db_engine")
def test_statcast_season_db_hit_skips_the_live_api(mock_engine, mock_fetch, mock_compute):
    mock_fetch.return_value = {"xba": 0.28}
    result = _get_statcast_season(660271, _PAST_SEASON, "hitting")
    mock_compute.assert_not_called()
    assert result == {"xba": 0.28}


@patch("client.season_stats_db.upsert_player_statcast_hitting_season")
@patch("client.statcast_season.compute_hitter_statcast_season")
@patch("client.season_stats_db.fetch_player_statcast_hitting_season")
@patch("client._db_engine")
def test_statcast_season_miss_falls_back_and_self_heals(mock_engine, mock_fetch, mock_compute, mock_upsert):
    mock_fetch.return_value = None
    mock_compute.return_value = {"xba": 0.25}
    result = _get_statcast_season(660271, _PAST_SEASON, "hitting")
    assert result == {"xba": 0.25}
    mock_upsert.assert_called_once_with(mock_engine.return_value, 660271, _PAST_SEASON, {"xba": 0.25})


@patch("client.statcast_season.compute_pitcher_statcast_season")
@patch("client.season_stats_db.fetch_player_statcast_pitching_season")
@patch("client._db_engine")
def test_statcast_season_current_season_never_touches_db(mock_engine, mock_fetch, mock_compute):
    mock_compute.return_value = {"cswPct": 0.3}
    _get_statcast_season(543037, _CURRENT_YEAR_SEASON, "pitching")
    mock_engine.assert_not_called()


@patch("client.statcast_season.compute_hitter_statcast_season")
@patch("client.season_stats_db.fetch_player_statcast_hitting_season")
@patch("client._db_engine")
def test_statcast_season_missing_secrets_config_falls_back_to_api(mock_engine, mock_fetch, mock_compute):
    mock_engine.side_effect = RuntimeError("no connection named 'postgresql'")
    mock_compute.return_value = {"xba": 0.25}
    assert _get_statcast_season(660271, _PAST_SEASON, "hitting") == {"xba": 0.25}


# ---------------------------------------------------------------------------
# _is_season_complete
# ---------------------------------------------------------------------------


def test_is_season_complete_true_for_a_past_season():
    assert client._is_season_complete(2015) is True


def test_is_season_complete_false_for_a_season_far_in_the_future():
    assert client._is_season_complete(_CURRENT_YEAR_SEASON) is False
