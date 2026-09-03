INSERT INTO player_season_team (
    player_id,
    team_id,
    season,
    position,
    is_pitcher
)
VALUES (
    :player_id,
    :team_id,
    :season,
    :position,
    :is_pitcher
)
ON CONFLICT (player_id, team_id, season)
DO UPDATE SET
    position = EXCLUDED.position,
    is_pitcher = EXCLUDED.is_pitcher;
