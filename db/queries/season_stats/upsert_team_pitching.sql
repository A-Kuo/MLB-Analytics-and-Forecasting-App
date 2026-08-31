INSERT INTO team_season_pitching (
    team_id,
    season,
    era,
    whip,
    strike_outs,
    base_on_balls,
    innings_pitched,
    earned_runs
)
VALUES (
    %(team_id)s,
    %(season)s,
    %(era)s,
    %(whip)s,
    %(strike_outs)s,
    %(base_on_balls)s,
    %(innings_pitched)s,
    %(earned_runs)s
)
ON CONFLICT (team_id, season)
DO UPDATE SET
    era = EXCLUDED.era,
    whip = EXCLUDED.whip,
    strike_outs = EXCLUDED.strike_outs,
    base_on_balls = EXCLUDED.base_on_balls,
    innings_pitched = EXCLUDED.innings_pitched,
    earned_runs = EXCLUDED.earned_runs;