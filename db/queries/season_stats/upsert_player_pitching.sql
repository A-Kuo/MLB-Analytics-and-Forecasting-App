INSERT INTO player_season_pitching_stats
    (player_id, season, era, whip, strikeouts, walks, innings_pitched, earned_runs)
VALUES
    (:player_id, :season, :era, :whip, :strikeouts, :walks, :innings_pitched, :earned_runs)
ON CONFLICT (player_id, season) DO UPDATE SET
    era = EXCLUDED.era, whip = EXCLUDED.whip, strikeouts = EXCLUDED.strikeouts,
    walks = EXCLUDED.walks, innings_pitched = EXCLUDED.innings_pitched,
    earned_runs = EXCLUDED.earned_runs;
