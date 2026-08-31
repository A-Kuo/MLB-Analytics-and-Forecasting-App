SELECT
    p.id AS player_id,
    p.name,
    p.debut_year,
    p.last_active_year,
    p.active,
    pst.team_id,
    pssp.csw_pct,
    pssp.whiff_pct,
    pssp.chase_pct,
    pssp.avg_velocity
FROM player_statcast_pitching_season AS pssp
JOIN players AS p
    ON p.id = pssp.player_id
JOIN player_season_team AS pst
    ON pst.player_id = pssp.player_id
   AND pst.season = pssp.season
WHERE pssp.season = %s
  AND pst.team_id = ANY(%s)
  AND pst.is_pitcher = TRUE;