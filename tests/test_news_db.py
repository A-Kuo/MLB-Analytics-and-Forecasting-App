"""Tests for macroservice/news_db.py.

Mocks the SQLAlchemy Engine/Connection, matching tests/test_season_stats_db.py's
pattern. See tests/test_news_db_integration.py for the opt-in real-database
round-trip.
"""
from __future__ import annotations

from unittest.mock import MagicMock

from macroservice import news_db


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
# fetch_team_news
# ---------------------------------------------------------------------------


def test_fetch_team_news_returns_empty_list_for_no_team_ids():
    engine = MagicMock()
    assert news_db.fetch_team_news(engine, ()) == []
    engine.connect.assert_not_called()


def test_fetch_team_news_maps_rows_to_dicts():
    rows = [{"team_id": 147, "source": "MLB", "headline": "H", "thumbnail": None, "link": "https://x", "published_at": "2024-01-01"}]
    engine, _ = _engine_returning_rows(rows)
    assert news_db.fetch_team_news(engine, (147,)) == rows


def test_fetch_team_news_passes_team_ids_as_a_list_with_limit_and_days():
    engine, conn = _engine_returning_rows([])
    news_db.fetch_team_news(engine, (147, 111), limit=5, days=3)
    _, params = conn.execute.call_args[0]
    assert isinstance(params["team_ids"], list)
    assert set(params["team_ids"]) == {147, 111}
    assert params["limit"] == 5
    assert params["days"] == 3


def test_fetch_team_news_orders_by_priority_then_recency():
    engine, conn = _engine_returning_rows([])
    news_db.fetch_team_news(engine, (147,))
    sql, _ = conn.execute.call_args[0]
    assert "ORDER BY priority ASC, published_at DESC" in str(sql)


# ---------------------------------------------------------------------------
# upsert_team_news
# ---------------------------------------------------------------------------


def test_upsert_team_news_is_a_noop_for_empty_rows():
    engine = MagicMock()
    news_db.upsert_team_news(engine, [])
    engine.begin.assert_not_called()


def test_upsert_team_news_executes_with_given_rows():
    engine, conn = _writable_engine()
    rows = [
        {
            "team_id": 147, "source": "MLB", "priority": 2, "headline": "H",
            "normalized_headline": "h", "thumbnail": None, "link": "https://x",
            "published_at": "2024-01-01",
        }
    ]
    news_db.upsert_team_news(engine, rows)
    _, params = conn.execute.call_args[0]
    assert params == rows


# ---------------------------------------------------------------------------
# delete_stale_news
# ---------------------------------------------------------------------------


def test_delete_stale_news_passes_days():
    engine, conn = _writable_engine()
    news_db.delete_stale_news(engine, days=14)
    _, params = conn.execute.call_args[0]
    assert params == {"days": 14}
