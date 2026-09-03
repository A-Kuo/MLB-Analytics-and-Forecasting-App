-- Template, not a runnable query as-is: {view}/{column}/{order} are
-- substituted in Python (macroservice/insights_db.py) from the fixed
-- per-metric registry there before this is wrapped in sqlalchemy.text(),
-- since which view/column/sort-direction to use depends on the caller's
-- chosen metric -- never from caller-supplied input directly, so this
-- isn't a SQL-injection surface despite the runtime substitution.
--
-- Queries v_insights_hitting/v_insights_pitching (db/views/) rather than
-- joining player_season_team + player_season_*_stats +
-- player_statcast_*_season + players by hand -- those views already do
-- that join once, as one source of truth shared with the Analytics page's
-- aggregate KPI/trend queries (lib/db/analytics.ts and macroservice/api.py's
-- _get_player_series both read the underlying tables the views wrap).
--
-- A plain SELECT DISTINCT (not DISTINCT ON + a subquery) is enough to
-- dedupe: the view is keyed by (player_id, season) on the stats side, not
-- (player_id, team_id, season), so a player traded between two
-- currently-selected teams produces duplicate IDENTICAL rows via the join
-- fan-out (same metric value both times), never duplicate values.
SELECT DISTINCT player_id, player_name AS name, debut_year, last_active_year, active,
       {column} AS metric_value
FROM {view}
WHERE season = :season AND team_id = ANY(:team_ids) AND {column} IS NOT NULL
ORDER BY {column} {order}
LIMIT :limit;
