SELECT game_date, opponent, at_bats, hits, home_runs, rbi, walks, strikeouts, avg
FROM player_game_log_hitting
WHERE player_id = :player_id AND season = :season
ORDER BY game_date, game_index;
