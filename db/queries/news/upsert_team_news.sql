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
    %(team_id)s,
    %(source)s,
    %(priority)s,
    %(headline)s,
    %(normalized_headline)s,
    %(thumbnail)s,
    %(link)s,
    %(published_at)s
)
ON CONFLICT (team_id, normalized_headline)
DO UPDATE SET
    source = EXCLUDED.source,
    priority = EXCLUDED.priority,
    headline = EXCLUDED.headline,
    thumbnail = EXCLUDED.thumbnail,
    link = EXCLUDED.link,
    published_at = EXCLUDED.published_at;