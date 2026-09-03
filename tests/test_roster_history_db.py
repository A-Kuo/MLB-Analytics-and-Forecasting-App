"""Tests for the Postgres roster-history cache.

Mocks the SQLAlchemy Engine/Connection rather than touching a real
database, matching how the rest of the suite mocks request_with_backoff
instead of calling the live MLB API. That verifies query shape and params
but can't catch genuine Postgres-dialect mistakes (text[] handling,
ON CONFLICT semantics) -- see tests/test_roster_history_db_integration.py
for the opt-in real-database round-trip that does.
"""
from __future__ import annotations

from unittest.mock import MagicMock

from macroservice import roster_history_db


def _engine_returning(rows: list[dict]):
    """An Engine whose connect() context yields the given mapping rows."""
    engine = MagicMock()
    conn = engine.connect.return_value.__enter__.return_value
    conn.execute.return_value.mappings.return_value.all.return_value = rows
    return engine, conn


def _writable_engine():
    """An Engine whose begin() context yields a recording connection."""
    engine = MagicMock()
    conn = engine.begin.return_value.__enter__.return_value
    return engine, conn


# ---------------------------------------------------------------------------
# fetch_team_roster_rows
# ---------------------------------------------------------------------------


def test_fetch_filters_by_team_id():
    engine, conn = _engine_returning([])
    roster_history_db.fetch_team_roster_rows(engine, 147)
    sql, params = conn.execute.call_args[0]
    assert params == {"team_id": 147}
    assert "rs.team_id = :team_id" in str(sql)


def test_fetch_returns_empty_list_when_team_has_no_rows():
    # The cache-miss signal client.py falls back on -- not an error.
    engine, _ = _engine_returning([])
    assert roster_history_db.fetch_team_roster_rows(engine, 147) == []


def test_fetch_returns_rows_in_the_shape_enrichment_expects():
    engine, _ = _engine_returning(
        [
            {
                "id": 1,
                "name": "Player One",
                "debut_year": 2015,
                "last_active_year": None,
                "active": True,
                "positions": ["SS"],
                "is_pitcher": False,
            }
        ]
    )
    rows = roster_history_db.fetch_team_roster_rows(engine, 147)
    assert rows == [
        {
            "id": 1,
            "name": "Player One",
            "debut_year": 2015,
            "last_active_year": None,
            "active": True,
            "positions": ["SS"],
            "is_pitcher": False,
        }
    ]


def test_fetch_normalizes_positions_to_a_plain_list():
    # psycopg may hand back its own sequence type for a text[] column;
    # downstream code does set(entry["positions"]), so it must be a list.
    engine, _ = _engine_returning(
        [
            {
                "id": 1,
                "name": "Outfielder",
                "debut_year": 2015,
                "last_active_year": 2020,
                "active": False,
                "positions": ("LF", "CF", "RF"),
                "is_pitcher": False,
            }
        ]
    )
    rows = roster_history_db.fetch_team_roster_rows(engine, 147)
    assert rows[0]["positions"] == ["LF", "CF", "RF"]
    assert isinstance(rows[0]["positions"], list)


# ---------------------------------------------------------------------------
# upsert_team_roster
# ---------------------------------------------------------------------------


_ROSTER = [
    {
        "id": 1,
        "name": "Player One",
        "positions": ["SS"],
        "is_pitcher": False,
        "debut_year": 2015,
        "last_active_year": None,
        "active": True,
        # Derived on read, never stored -- upsert must ignore these.
        "active_year_ranges": [(2015, None)],
        "active_years_label": "2015–present",
    }
]


def test_upsert_writes_players_then_stints_in_one_transaction():
    engine, conn = _writable_engine()
    roster_history_db.upsert_team_roster(engine, 147, _ROSTER)
    engine.begin.assert_called_once()  # both writes share one transaction
    assert conn.execute.call_count == 2
    first_sql = str(conn.execute.call_args_list[0][0][0])
    second_sql = str(conn.execute.call_args_list[1][0][0])
    assert "INSERT INTO players" in first_sql  # FK parent first
    assert "INSERT INTO roster_stints" in second_sql


def test_upsert_player_params_exclude_derived_keys():
    engine, conn = _writable_engine()
    roster_history_db.upsert_team_roster(engine, 147, _ROSTER)
    player_params = conn.execute.call_args_list[0][0][1]
    assert player_params == [
        {"id": 1, "name": "Player One", "debut_year": 2015, "last_active_year": None, "active": True}
    ]


def test_upsert_stint_params_carry_team_id_and_positions():
    engine, conn = _writable_engine()
    roster_history_db.upsert_team_roster(engine, 147, _ROSTER)
    stint_params = conn.execute.call_args_list[1][0][1]
    assert stint_params == [{"team_id": 147, "player_id": 1, "positions": ["SS"], "is_pitcher": False}]


def test_upsert_is_idempotent_via_on_conflict_clauses():
    # Whitespace-normalized: the SQL now loads from db/queries/roster_history/
    # *.sql (see macroservice/sql.load_query), formatted as a readable
    # multi-line file rather than a single-line inline string -- same
    # ON CONFLICT clause, just not literally on one line anymore.
    engine, conn = _writable_engine()
    roster_history_db.upsert_team_roster(engine, 147, _ROSTER)
    statements = [" ".join(str(call[0][0]).split()) for call in conn.execute.call_args_list]
    assert "ON CONFLICT (id) DO UPDATE" in statements[0]
    assert "ON CONFLICT (team_id, player_id) DO UPDATE" in statements[1]


def test_upsert_empty_roster_writes_nothing():
    # Guards against a failed API fetch blanking a team's cached rows.
    engine, _ = _writable_engine()
    roster_history_db.upsert_team_roster(engine, 147, [])
    engine.begin.assert_not_called()
