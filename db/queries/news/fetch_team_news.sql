SELECT
    team_id,
    source,
    priority,
    headline,
    thumbnail,
    link,
    published_at
FROM team_news
WHERE team_id = ANY(%s)
  AND published_at >= NOW() - make_interval(days => %s)
ORDER BY
    published_at DESC,
    priority ASC,
    headline ASC
LIMIT %s;