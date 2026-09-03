INSERT INTO player_game_log_pitching
    (player_id, season, game_date, game_index, opponent, innings_pitched, hits, earned_runs, strikeouts, walks, era)
VALUES
    (:player_id, :season, :game_date, :game_index, :opponent, :innings_pitched, :hits, :earned_runs, :strikeouts, :walks, :era)
ON CONFLICT (player_id, season, game_date, game_index) DO UPDATE SET
    opponent = EXCLUDED.opponent, innings_pitched = EXCLUDED.innings_pitched, hits = EXCLUDED.hits,
    earned_runs = EXCLUDED.earned_runs, strikeouts = EXCLUDED.strikeouts, walks = EXCLUDED.walks, era = EXCLUDED.era;
