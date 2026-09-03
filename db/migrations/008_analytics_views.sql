-- Pre-joined player/season/team/metric views for Insights and Analytics --
-- see db/views/*.sql for each view's own source-of-truth definition and
-- rationale; kept here as one BEGIN/COMMIT-wrapped migration so a fresh
-- database gets them in one step alongside every other table.

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
    psh.strikeouts,
    psh.walks,
    pssh.xba,
    pssh.avg_exit_velocity,
    pssh.hard_hit_pct,
    pssh.barrel_pct
FROM player_season_team AS pst
JOIN players AS p
    ON p.id = pst.player_id
LEFT JOIN player_season_hitting_stats AS psh
    ON psh.player_id = pst.player_id
   AND psh.season = pst.season
LEFT JOIN player_statcast_hitting_season AS pssh
    ON pssh.player_id = pst.player_id
   AND pssh.season = pst.season
WHERE pst.is_pitcher = FALSE;

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

-- Domain-named wrappers for the Insights leaderboard specifically (same
-- underlying join, kept as one source of truth in the two views above).
CREATE OR REPLACE VIEW v_insights_hitting AS
SELECT * FROM v_player_season_hitting_metrics;

CREATE OR REPLACE VIEW v_insights_pitching AS
SELECT * FROM v_player_season_pitching_metrics;
