SELECT
    player_id,
    season,
    era,
    whip,
    strike_outs,
    base_on_balls,
    innings_pitched,
    earned_runs
FROM player_season_pitching
WHERE player_id = %s
  AND season = %s;