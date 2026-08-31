SELECT
    player_id,
    season,
    avg,
    obp,
    slg,
    ops,
    home_runs,
    rbi,
    strike_outs,
    base_on_balls
FROM player_season_hitting
WHERE player_id = %s
  AND season = %s;