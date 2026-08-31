SELECT
    p.id AS player_id,
    p.name,
    p.debut_year,
    p.last_active_year,
    p.active,
    pst.team_id,
    pssh.xba,
    pssh.avg_exit_velocity,
    pssh.hard_hit_pct,
    pssh.barrel_pct
FROM player_statcast_hitting_season AS pssh
JOIN players AS p
    ON p.id = pssh.player_id
JOIN player_season_team AS pst
    ON pst.player_id = pssh.player_id
   AND pst.season = pssh.season
WHERE pssh.season = %s
  AND pst.team_id = ANY(%s)
  AND pst.is_pitcher = FALSE;