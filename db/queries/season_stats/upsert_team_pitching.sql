INSERT INTO team_season_pitching_stats (team_id, season, wins, losses, runs_allowed, era, whip, games_played)
VALUES (:team_id, :season, :wins, :losses, :runs_allowed, :era, :whip, :games_played)
ON CONFLICT (team_id, season) DO UPDATE SET
    wins = EXCLUDED.wins, losses = EXCLUDED.losses, runs_allowed = EXCLUDED.runs_allowed,
    era = EXCLUDED.era, whip = EXCLUDED.whip, games_played = EXCLUDED.games_played;
