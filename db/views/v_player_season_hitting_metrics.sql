CREATE OR REPLACE VIEW v_player_season_hitting_metrics AS
SELECT
    pst.season,
    pst.team_id,
    pst.player_id,
    p.name AS player_name,
    p.debut_year,
    p.last_active_year,
    p.active,
    pst.position,
    psh.avg,
    psh.obp,
    psh.slg,
    psh.ops,
    psh.home_runs,
    psh.rbi,
    psh.strike_outs,
    psh.base_on_balls,
    pssh.xba,
    pssh.avg_exit_velocity,
    pssh.hard_hit_pct,
    pssh.barrel_pct
FROM player_season_team AS pst
JOIN players AS p
    ON p.id = pst.player_id
LEFT JOIN player_season_hitting AS psh
    ON psh.player_id = pst.player_id
   AND psh.season = pst.season
LEFT JOIN player_statcast_hitting_season AS pssh
    ON pssh.player_id = pst.player_id
   AND pssh.season = pst.season
WHERE pst.is_pitcher = FALSE;