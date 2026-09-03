SELECT era, whip, strikeouts, walks, innings_pitched, earned_runs
FROM player_season_pitching_stats
WHERE player_id = :player_id AND season = :season;
