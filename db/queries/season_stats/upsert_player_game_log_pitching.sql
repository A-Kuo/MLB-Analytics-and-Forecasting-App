INSERT INTO player_game_log_pitching (
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
)
VALUES (
    %(player_id)s,
    %(season)s,
    %(game_date)s,
    %(opponent)s,
    %(innings_pitched)s,
    %(hits)s,
    %(earned_runs)s,
    %(strike_outs)s,
    %(base_on_balls)s,
    %(era)s
)
ON CONFLICT (player_id, season, game_date, opponent)
DO UPDATE SET
    innings_pitched = EXCLUDED.innings_pitched,
    hits = EXCLUDED.hits,
    earned_runs = EXCLUDED.earned_runs,
    strike_outs = EXCLUDED.strike_outs,
    base_on_balls = EXCLUDED.base_on_balls,
    era = EXCLUDED.era;