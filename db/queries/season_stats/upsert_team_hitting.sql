INSERT INTO team_season_hitting (
    team_id,
    season,
    avg,
    obp,
    slg,
    ops,
    home_runs,
    rbi,
    strike_outs,
    base_on_balls
)
VALUES (
    %(team_id)s,
    %(season)s,
    %(avg)s,
    %(obp)s,
    %(slg)s,
    %(ops)s,
    %(home_runs)s,
    %(rbi)s,
    %(strike_outs)s,
    %(base_on_balls)s
)
ON CONFLICT (team_id, season)
DO UPDATE SET
    avg = EXCLUDED.avg,
    obp = EXCLUDED.obp,
    slg = EXCLUDED.slg,
    ops = EXCLUDED.ops,
    home_runs = EXCLUDED.home_runs,
    rbi = EXCLUDED.rbi,
    strike_outs = EXCLUDED.strike_outs,
    base_on_balls = EXCLUDED.base_on_balls;