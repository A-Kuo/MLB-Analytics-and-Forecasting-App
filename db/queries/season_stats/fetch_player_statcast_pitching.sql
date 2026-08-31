SELECT
    player_id,
    season,
    csw_pct,
    whiff_pct,
    chase_pct,
    avg_velocity
FROM player_statcast_pitching_season
WHERE player_id = %s
  AND season = %s;