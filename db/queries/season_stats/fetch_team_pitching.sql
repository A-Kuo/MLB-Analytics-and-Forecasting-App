SELECT
    team_id,
    season,
    era,
    whip,
    strike_outs,
    base_on_balls,
    innings_pitched,
    earned_runs
FROM team_season_pitching
WHERE team_id = %s
  AND season = %s;