INSERT INTO team_news (
    team_id,
    source,
    priority,
    headline,
    normalized_headline,
    thumbnail,
    link,
    published_at
)
VALUES (
    :team_id,
    :source,
    :priority,
    :headline,
    :normalized_headline,
    :thumbnail,
    :link,
    :published_at
)
ON CONFLICT (team_id, normalized_headline)
DO UPDATE SET
    source = EXCLUDED.source,
    priority = EXCLUDED.priority,
    thumbnail = EXCLUDED.thumbnail,
    link = EXCLUDED.link,
    published_at = EXCLUDED.published_at,
    ingested_at = now();
