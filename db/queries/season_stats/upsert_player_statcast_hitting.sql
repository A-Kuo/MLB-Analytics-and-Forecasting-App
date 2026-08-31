INSERT INTO player_statcast_hitting_season (
    player_id,
    season,
    xba,
    avg_exit_velocity,
    hard_hit_pct,
    barrel_pct
)
VALUES (
    %(player_id)s,
    %(season)s,
    %(xba)s,
    %(avg_exit_velocity)s,
    %(hard_hit_pct)s,
    %(barrel_pct)s
)
ON CONFLICT (player_id, season)
DO UPDATE SET
    xba = EXCLUDED.xba,
    avg_exit_velocity = EXCLUDED.avg_exit_velocity,
    hard_hit_pct = EXCLUDED.hard_hit_pct,
    barrel_pct = EXCLUDED.barrel_pct;