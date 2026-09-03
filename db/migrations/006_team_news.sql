-- Pre-ingested team news (scripts/ingest_team_news.py, run on a schedule
-- via .github/workflows/ingest_team_news.yml -- see
-- macroservice/config/news_sources.py for which sources feed this and
-- why). Moved off the Streamlit request path entirely: client.py's News
-- Feed reads only from this table (macroservice/news_db.py), with no
-- live-API fallback -- an empty result means the ingestion job hasn't run
-- yet or found nothing in the last 7 days, not a transient failure to
-- retry inline. team_id, not team_name, to match every other table here.
CREATE TABLE IF NOT EXISTS team_news (
    id                  BIGSERIAL PRIMARY KEY,
    team_id             INTEGER NOT NULL,
    source              TEXT NOT NULL,
    priority            INTEGER NOT NULL,
    headline            TEXT NOT NULL,
    normalized_headline TEXT NOT NULL,
    thumbnail           TEXT,
    link                TEXT NOT NULL,
    published_at        TIMESTAMPTZ NOT NULL,
    ingested_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- One row per (team, distinct headline text) -- re-ingesting the same
    -- article updates it in place rather than duplicating it.
    CONSTRAINT uq_team_news_headline UNIQUE (team_id, normalized_headline)
);
-- Index created in 007_indexes.sql, alongside every other table's.
