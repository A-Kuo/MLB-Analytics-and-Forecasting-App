SELECT
    player_id,
    season,
    xba,
    avg_exit_velocity,
    hard_hit_pct,
    barrel_pct
FROM player_statcast_hitting_season
WHERE player_id = %s
  AND season = %s;