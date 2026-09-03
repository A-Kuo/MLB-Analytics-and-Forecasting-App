SELECT runs, avg, obp, slg, ops, games_played
FROM team_season_hitting_stats
WHERE team_id = :team_id AND season = :season;
