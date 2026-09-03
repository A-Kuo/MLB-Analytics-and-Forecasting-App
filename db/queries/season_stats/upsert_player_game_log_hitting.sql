INSERT INTO player_game_log_hitting
    (player_id, season, game_date, game_index, opponent, at_bats, hits, home_runs, rbi, walks, strikeouts, avg)
VALUES
    (:player_id, :season, :game_date, :game_index, :opponent, :at_bats, :hits, :home_runs, :rbi, :walks, :strikeouts, :avg)
ON CONFLICT (player_id, season, game_date, game_index) DO UPDATE SET
    opponent = EXCLUDED.opponent, at_bats = EXCLUDED.at_bats, hits = EXCLUDED.hits,
    home_runs = EXCLUDED.home_runs, rbi = EXCLUDED.rbi, walks = EXCLUDED.walks,
    strikeouts = EXCLUDED.strikeouts, avg = EXCLUDED.avg;
