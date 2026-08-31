INSERT INTO player_statcast_pitching_season (
    player_id,
    season,
    csw_pct,
    whiff_pct,
    chase_pct,
    avg_velocity
)
VALUES (
    %(player_id)s,
    %(season)s,
    %(csw_pct)s,
    %(whiff_pct)s,
    %(chase_pct)s,
    %(avg_velocity)s
)
ON CONFLICT (player_id, season)
DO UPDATE SET
    csw_pct = EXCLUDED.csw_pct,
    whiff_pct = EXCLUDED.whiff_pct,
    chase_pct = EXCLUDED.chase_pct,
    avg_velocity = EXCLUDED.avg_velocity;