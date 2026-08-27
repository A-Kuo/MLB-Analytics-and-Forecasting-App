"""Real-Postgres round-trip for macroservice/news_db.py.

Skipped unless DATABASE_URL is set (or a local .streamlit/secrets.toml
exists), mirroring tests/test_season_stats_db_integration.py's rationale.

Uses team ids far outside any real MLB id range so they can't collide with
cached data for an actual team, and cleans up after itself.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, text

from macroservice import db, news_db

DATABASE_URL = db.resolve_database_url()

pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="requires DATABASE_URL or a local .streamlit/secrets.toml"
)

TEAM_A = 999_301
TEAM_B = 999_302


@pytest.fixture
def engine():
    eng = create_engine(DATABASE_URL)
    db.ensure_schema(eng)
    yield eng
    with eng.begin() as conn:
        conn.execute(text("DELETE FROM team_news WHERE team_id IN (:a, :b)"), {"a": TEAM_A, "b": TEAM_B})
    eng.dispose()


def _row(team_id: int, source: str, priority: int, headline: str, published_at) -> dict:
    return {
        "team_id": team_id, "source": source, "priority": priority, "headline": headline,
        "normalized_headline": headline.lower(), "thumbnail": None,
        "link": f"https://example.com/{headline}", "published_at": published_at,
    }


def test_upsert_and_fetch_round_trip(engine):
    now = datetime.now(timezone.utc)
    news_db.upsert_team_news(engine, [_row(TEAM_A, "MLB", 2, "Test Headline", now)])
    result = news_db.fetch_team_news(engine, (TEAM_A,))
    assert len(result) == 1
    assert result[0]["headline"] == "Test Headline"


def test_upsert_overwrites_in_place_on_conflict(engine):
    now = datetime.now(timezone.utc)
    news_db.upsert_team_news(engine, [_row(TEAM_A, "MLB", 2, "Same Headline", now)])
    news_db.upsert_team_news(engine, [_row(TEAM_A, "SBNation", 1, "Same Headline", now)])
    result = news_db.fetch_team_news(engine, (TEAM_A,))
    assert len(result) == 1  # updated in place, not duplicated
    assert result[0]["source"] == "SBNation"


def test_fetch_orders_by_priority_then_recency_across_teams(engine):
    now = datetime.now(timezone.utc)
    news_db.upsert_team_news(
        engine,
        [
            _row(TEAM_A, "MLB", 2, "Team A MLB Story", now),
            _row(TEAM_B, "SBNation", 1, "Team B SBNation Story", now - timedelta(hours=2)),
        ],
    )
    result = news_db.fetch_team_news(engine, (TEAM_A, TEAM_B))
    # Team B's SBNation story (priority 1) ranks ahead of Team A's MLB
    # story (priority 2) despite publishing earlier.
    assert result[0]["headline"] == "Team B SBNation Story"
    assert result[1]["headline"] == "Team A MLB Story"


def test_fetch_excludes_articles_outside_the_lookback_window(engine):
    old = datetime.now(timezone.utc) - timedelta(days=30)
    news_db.upsert_team_news(engine, [_row(TEAM_A, "MLB", 2, "Old Story", old)])
    result = news_db.fetch_team_news(engine, (TEAM_A,), days=7)
    assert result == []


def test_delete_stale_news_removes_old_rows_only(engine):
    now = datetime.now(timezone.utc)
    old = now - timedelta(days=30)
    news_db.upsert_team_news(
        engine,
        [_row(TEAM_A, "MLB", 2, "Fresh Story", now), _row(TEAM_A, "MLB", 2, "Stale Story", old)],
    )
    news_db.delete_stale_news(engine, days=7)
    with engine.connect() as conn:
        headlines = {
            row[0]
            for row in conn.execute(text("SELECT headline FROM team_news WHERE team_id = :t"), {"t": TEAM_A})
        }
    assert headlines == {"Fresh Story"}
