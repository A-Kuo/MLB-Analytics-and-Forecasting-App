"""Tests for client.py's Postgres-first / live-API-fallback roster path.

The fallback is the property that keeps the dashboard working when the
cache is unavailable -- an unconfigured secrets.toml, a Neon outage, or a
team the backfill hasn't covered yet all have to degrade to the live API
rather than erroring. These exercise the undecorated functions
(``__wrapped__``) so Streamlit's cache doesn't carry results between
tests or need a script run context.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import client

_DB_ROWS = [
    {
        "id": 1,
        "name": "Cached Player",
        "positions": ["SS"],
        "is_pitcher": False,
        "debut_year": 2015,
        "last_active_year": None,
        "active": True,
    }
]

_API_ROSTER = [
    {
        "id": 2,
        "name": "Live Player",
        "positions": ["CF"],
        "is_pitcher": False,
        "debut_year": 2018,
        "last_active_year": None,
        "active": True,
        "active_year_ranges": [(2018, None)],
        "active_years_label": "2018–present",
    }
]

_get_roster = client.get_team_roster_with_active_years.__wrapped__
_resolve = client.resolve_players_in_range.__wrapped__


@patch("client.roster_history.get_team_roster_with_active_years")
@patch("client.roster_history_db.fetch_team_roster_rows")
@patch("client._db_engine")
def test_db_hit_skips_the_live_api(mock_engine, mock_fetch, mock_api):
    mock_fetch.return_value = _DB_ROWS
    roster = _get_roster(147)
    mock_api.assert_not_called()
    assert roster[0]["name"] == "Cached Player"
    # Enrichment still happens on read, from the raw stored columns.
    assert roster[0]["active_year_ranges"] == [(2015, None)]
    assert roster[0]["active_years_label"] == "2015–present"


@patch("client.roster_history_db.upsert_team_roster")
@patch("client.roster_history.get_team_roster_with_active_years")
@patch("client.roster_history_db.fetch_team_roster_rows")
@patch("client._db_engine")
def test_empty_db_falls_back_to_api_and_self_heals(mock_engine, mock_fetch, mock_api, mock_upsert):
    mock_fetch.return_value = []  # team not backfilled yet
    mock_api.return_value = _API_ROSTER
    roster = _get_roster(147)
    assert roster == _API_ROSTER
    mock_upsert.assert_called_once()
    assert mock_upsert.call_args[0][1] == 147
    assert mock_upsert.call_args[0][2] == _API_ROSTER


@patch("client.roster_history_db.upsert_team_roster")
@patch("client.roster_history.get_team_roster_with_active_years")
@patch("client.roster_history_db.fetch_team_roster_rows")
@patch("client._db_engine")
def test_db_read_error_falls_back_to_api(mock_engine, mock_fetch, mock_api, mock_upsert):
    mock_fetch.side_effect = RuntimeError("connection refused")
    mock_api.return_value = _API_ROSTER
    assert _get_roster(147) == _API_ROSTER


@patch("client.roster_history_db.upsert_team_roster")
@patch("client.roster_history.get_team_roster_with_active_years")
@patch("client.roster_history_db.fetch_team_roster_rows")
@patch("client._db_engine")
def test_upsert_error_still_serves_live_data(mock_engine, mock_fetch, mock_api, mock_upsert):
    mock_fetch.return_value = []
    mock_api.return_value = _API_ROSTER
    mock_upsert.side_effect = RuntimeError("read-only transaction")
    assert _get_roster(147) == _API_ROSTER  # write failure must not surface


@patch("client.roster_history.get_team_roster_with_active_years")
@patch("client.roster_history_db.fetch_team_roster_rows")
@patch("client._db_engine")
def test_missing_secrets_config_falls_back_to_api(mock_engine, mock_fetch, mock_api):
    # No .streamlit/secrets.toml -> st.connection raises; the dashboard has
    # to keep working exactly as it did before this migration.
    mock_engine.side_effect = RuntimeError("no connection named 'postgresql'")
    mock_api.return_value = _API_ROSTER
    assert _get_roster(147) == _API_ROSTER


@patch("client.get_team_roster_with_active_years")
def test_resolve_reuses_one_roster_fetch_per_call(mock_get_roster):
    mock_get_roster.return_value = _API_ROSTER
    assert _resolve(147, 2015, 2026, frozenset({"CF"})) == {2}
    assert _resolve(147, 2015, 2026, frozenset({"SS"})) == set()
    # Each per-position call goes through the cached roster getter rather
    # than re-resolving from the API itself.
    assert mock_get_roster.call_count == 2
