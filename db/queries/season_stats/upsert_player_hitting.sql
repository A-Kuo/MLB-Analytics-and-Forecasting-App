INSERT INTO player_season_hitting_stats
    (player_id, season, avg, obp, slg, ops, home_runs, rbi, strikeouts, walks)
VALUES
    (:player_id, :season, :avg, :obp, :slg, :ops, :home_runs, :rbi, :strikeouts, :walks)
ON CONFLICT (player_id, season) DO UPDATE SET
    avg = EXCLUDED.avg, obp = EXCLUDED.obp, slg = EXCLUDED.slg, ops = EXCLUDED.ops,
    home_runs = EXCLUDED.home_runs, rbi = EXCLUDED.rbi,
    strikeouts = EXCLUDED.strikeouts, walks = EXCLUDED.walks;
