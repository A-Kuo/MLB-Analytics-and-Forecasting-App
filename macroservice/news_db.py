"""Postgres-backed storage for pre-ingested team news (db/schema.sql's
team_news table, populated by scripts/ingest_team_news.py).

Same shape as macroservice/season_stats_db.py and macroservice/insights_db.py
-- every function takes an already-open SQLAlchemy Engine, Streamlit-free,
so the same code serves client.py (via st.connection) and the standalone
ingestion script.

Unlike the season-stats caches, there is no live-API fallback anywhere
above this module: client.get_team_news reads only from here. An empty
result means the ingestion job hasn't run yet (or found nothing for that
team in the lookback window), not a transient failure worth retrying live.
"""
from __future__ import annotations

from sqlalchemy import Engine, text

_FETCH_SQL = text("""
    SELECT team_id, source, headline, thumbnail, link, published_at
    FROM team_news
    WHERE team_id = ANY(:team_ids) AND published_at >= now() - make_interval(days => :days)
    ORDER BY priority ASC, published_at DESC
    LIMIT :limit
""")

_UPSERT_SQL = text("""
    INSERT INTO team_news
        (team_id, source, priority, headline, normalized_headline, thumbnail, link, published_at)
    VALUES
        (:team_id, :source, :priority, :headline, :normalized_headline, :thumbnail, :link, :published_at)
    ON CONFLICT (team_id, normalized_headline) DO UPDATE SET
        source = EXCLUDED.source, priority = EXCLUDED.priority, thumbnail = EXCLUDED.thumbnail,
        link = EXCLUDED.link, published_at = EXCLUDED.published_at, ingested_at = now()
""")

_CLEANUP_SQL = text("DELETE FROM team_news WHERE published_at < now() - make_interval(days => :days)")


def fetch_team_news(engine: Engine, team_ids: tuple[int, ...], limit: int = 10, days: int = 7) -> list[dict]:
    """Top ``limit`` headlines across every team in ``team_ids``, ordered
    by source priority then recency -- one query does the cross-team merge
    that a Python-side combine would otherwise need, since that's exactly
    what SQL's ORDER BY already does.
    """
    if not team_ids:
        return []
    with engine.connect() as conn:
        rows = conn.execute(_FETCH_SQL, {"team_ids": list(team_ids), "limit": limit, "days": days}).mappings().all()
    return [dict(row) for row in rows]


def upsert_team_news(engine: Engine, rows: list[dict]) -> None:
    """``rows``: the shape macroservice.news.fetch_team_articles returns,
    plus a ``team_id`` key. A no-op for an empty list (a team with zero
    fresh articles this run shouldn't touch its existing cached rows).
    """
    if not rows:
        return
    with engine.begin() as conn:
        conn.execute(_UPSERT_SQL, rows)


def delete_stale_news(engine: Engine, days: int = 7) -> None:
    """Purges anything older than the lookback window -- called once per
    ingestion run so the table stays small (an ephemeral cache, not an
    archive).
    """
    with engine.begin() as conn:
        conn.execute(_CLEANUP_SQL, {"days": days})
