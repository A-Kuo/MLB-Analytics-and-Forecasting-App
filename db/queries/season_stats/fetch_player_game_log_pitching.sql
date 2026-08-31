SELECT
    player_id,
    season,
    game_date,
    opponent,
    innings_pitched,
    hits,
    earned_runs,
    strike_outs,
    base_on_balls,
    era
FROM player_game_log_pitching
WHERE player_id = %s
  AND season = %s
ORDER BY game_date ASC;