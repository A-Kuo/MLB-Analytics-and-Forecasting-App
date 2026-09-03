INSERT INTO team_season_hitting_stats (team_id, season, runs, avg, obp, slg, ops, games_played)
VALUES (:team_id, :season, :runs, :avg, :obp, :slg, :ops, :games_played)
ON CONFLICT (team_id, season) DO UPDATE SET
    runs = EXCLUDED.runs, avg = EXCLUDED.avg, obp = EXCLUDED.obp, slg = EXCLUDED.slg,
    ops = EXCLUDED.ops, games_played = EXCLUDED.games_played;
