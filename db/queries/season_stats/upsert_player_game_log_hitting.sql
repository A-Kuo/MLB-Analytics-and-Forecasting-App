INSERT INTO player_game_log_hitting (
    player_id,
    season,
    game_date,
    opponent,
    at_bats,
    hits,
    home_runs,
    rbi,
    base_on_balls,
    strike_outs,
    avg
)
VALUES (
    %(player_id)s,
    %(season)s,
    %(game_date)s,
    %(opponent)s,
    %(at_bats)s,
    %(hits)s,
    %(home_runs)s,
    %(rbi)s,
    %(base_on_balls)s,
    %(strike_outs)s,
    %(avg)s
)
ON CONFLICT (player_id, season, game_date, opponent)
DO UPDATE SET
    at_bats = EXCLUDED.at_bats,
    hits = EXCLUDED.hits,
    home_runs = EXCLUDED.home_runs,
    rbi = EXCLUDED.rbi,
    base_on_balls = EXCLUDED.base_on_balls,
    strike_outs = EXCLUDED.strike_outs,
    avg = EXCLUDED.avg;