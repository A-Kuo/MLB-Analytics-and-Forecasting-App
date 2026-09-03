INSERT INTO roster_stints (
    team_id,
    player_id,
    positions,
    is_pitcher
)
VALUES (
    :team_id,
    :player_id,
    :positions,
    :is_pitcher
)
ON CONFLICT (team_id, player_id)
DO UPDATE SET
    positions = EXCLUDED.positions,
    is_pitcher = EXCLUDED.is_pitcher;
