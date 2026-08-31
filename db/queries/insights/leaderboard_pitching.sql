SELECT
    p.id AS player_id,
    p.name,
    p.debut_year,
    p.last_active_year,
    p.active,
    pst.team_id,
    psp.era,
    psp.whip,
    psp.strike_outs,
    psp.base_on_balls,
    psp.innings_pitched,
    psp.earned_runs
FROM player_season_pitching AS psp
JOIN players AS p
    ON p.id = psp.player_id
JOIN player_season_team AS pst
    ON pst.player_id = psp.player_id
   AND pst.season = psp.season
WHERE psp.season = %s
  AND pst.team_id = ANY(%s)
  AND pst.is_pitcher = TRUE;