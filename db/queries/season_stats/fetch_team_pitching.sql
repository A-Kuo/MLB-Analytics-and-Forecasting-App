SELECT wins, losses, runs_allowed, era, whip, games_played
FROM team_season_pitching_stats
WHERE team_id = :team_id AND season = :season;
