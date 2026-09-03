CREATE OR REPLACE VIEW v_player_season_pitching_metrics AS
SELECT
    pst.season,
    pst.team_id,
    pst.player_id,
    p.name AS player_name,
    p.debut_year,
    p.last_active_year,
    p.active,
    pst.position,
    psp.era,
    psp.whip,
    psp.strikeouts,
    psp.walks,
    psp.innings_pitched,
    psp.earned_runs,
    pssp.csw_pct,
    pssp.whiff_pct,
    pssp.chase_pct,
    pssp.avg_velocity
FROM player_season_team AS pst
JOIN players AS p
    ON p.id = pst.player_id
LEFT JOIN player_season_pitching_stats AS psp
    ON psp.player_id = pst.player_id
   AND psp.season = pst.season
LEFT JOIN player_statcast_pitching_season AS pssp
    ON pssp.player_id = pst.player_id
   AND pssp.season = pst.season
WHERE pst.is_pitcher = TRUE;