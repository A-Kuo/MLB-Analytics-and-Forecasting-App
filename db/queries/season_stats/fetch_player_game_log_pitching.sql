SELECT game_date, opponent, innings_pitched, hits, earned_runs, strikeouts, walks, era
FROM player_game_log_pitching
WHERE player_id = :player_id AND season = :season
ORDER BY game_date, game_index;
