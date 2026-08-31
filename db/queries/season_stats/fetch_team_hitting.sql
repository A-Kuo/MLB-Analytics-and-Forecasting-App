SELECT
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
FROM team_season_hitting
WHERE team_id = %s
  AND season = %s;