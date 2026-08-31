INSERT INTO player_season_team (
    player_id,
    team_id,
    season,
    position,
    is_pitcher
)
VALUES (
    %(player_id)s,
    %(team_id)s,
    %(season)s,
    %(position)s,
    %(is_pitcher)s
)
ON CONFLICT (player_id, team_id, season)
DO UPDATE SET
    position = EXCLUDED.position,
    is_pitcher = EXCLUDED.is_pitcher;