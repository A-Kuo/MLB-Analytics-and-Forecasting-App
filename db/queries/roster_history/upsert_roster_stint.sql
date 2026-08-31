INSERT INTO roster_stints (
    team_id,
    player_id,
    positions,
    is_pitcher
)
VALUES (
    %(team_id)s,
    %(player_id)s,
    %(positions)s,
    %(is_pitcher)s
)
ON CONFLICT (team_id, player_id)
DO UPDATE SET
    positions = EXCLUDED.positions,
    is_pitcher = EXCLUDED.is_pitcher;