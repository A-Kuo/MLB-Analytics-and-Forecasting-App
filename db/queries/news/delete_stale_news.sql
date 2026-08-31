DELETE FROM team_news
WHERE published_at < NOW() - make_interval(days => %s);