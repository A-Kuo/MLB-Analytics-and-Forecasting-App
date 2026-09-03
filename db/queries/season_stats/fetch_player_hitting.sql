SELECT avg, obp, slg, ops, home_runs, rbi, strikeouts, walks
FROM player_season_hitting_stats
WHERE player_id = :player_id AND season = :season;
