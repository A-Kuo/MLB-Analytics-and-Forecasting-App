DELETE FROM team_news
WHERE published_at < now() - make_interval(days => :days);
