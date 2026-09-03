SELECT id, team_id, source, headline, thumbnail, link, published_at
FROM team_news
WHERE team_id = ANY(:team_ids) AND published_at >= now() - make_interval(days => :days)
ORDER BY priority ASC, published_at DESC
LIMIT :limit;
