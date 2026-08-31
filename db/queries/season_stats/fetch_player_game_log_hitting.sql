/* 
Do not write these blindly until you copy the exact JSON/column schema 
from db/schema.sql and macroservice/season_stats_db.py. 
The game-log table design may store flattened columns, 
JSONB payloads, composite keys, or different hitting/pitching fields.

The following is the recommended shape if the tables are flattened.
*/

SELECT
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
FROM player_game_log_hitting
WHERE player_id = %s
  AND season = %s
ORDER BY game_date ASC;