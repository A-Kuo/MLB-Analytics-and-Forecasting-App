SELECT
    p.id AS player_id,
    p.name,
    p.debut_year,
    p.last_active_year,
    p.active,
    pst.team_id,
    psh.avg,
    psh.obp,
    psh.slg,
    psh.ops,
    psh.home_runs,
    psh.rbi,
    psh.strike_outs,
    psh.base_on_balls
FROM player_season_hitting AS psh
JOIN players AS p
    ON p.id = psh.player_id
JOIN player_season_team AS pst
    ON pst.player_id = psh.player_id
   AND pst.season = psh.season
WHERE psh.season = %s
  AND pst.team_id = ANY(%s)
  AND pst.is_pitcher = FALSE;