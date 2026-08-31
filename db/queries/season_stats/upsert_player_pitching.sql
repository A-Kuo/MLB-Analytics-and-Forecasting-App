INSERT INTO player_season_pitching (
    player_id,
    season,
    era,
    whip,
    strike_outs,
    base_on_balls,
    innings_pitched,
    earned_runs
)
VALUES (
    %(player_id)s,
    %(season)s,
    %(era)s,
    %(whip)s,
    %(strike_outs)s,
    %(base_on_balls)s,
    %(innings_pitched)s,
    %(earned_runs)s
)
ON CONFLICT (player_id, season)
DO UPDATE SET
    era = EXCLUDED.era,
    whip = EXCLUDED.whip,
    strike_outs = EXCLUDED.strike_outs,
    base_on_balls = EXCLUDED.base_on_balls,
    innings_pitched = EXCLUDED.innings_pitched,
    earned_runs = EXCLUDED.earned_runs;