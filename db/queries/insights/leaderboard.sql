-- Template, not a runnable query as-is: {view}/{column}/{order} are
-- substituted in Python (macroservice/insights_db.py) from the fixed
-- per-metric registry there before this is wrapped in sqlalchemy.text(),
-- since which view/column/sort-direction to use depends on the caller's
-- chosen metric -- never from caller-supplied input directly, so this
-- isn't a SQL-injection surface despite the runtime template substitution.
--
-- Queries v_insights_hitting/v_insights_pitching (db/views/) rather than
-- joining player_season_team + player_season_*_stats +
-- player_statcast_*_season + players by hand -- those views already do
-- that join once, as one source of truth shared with the Analytics page's
-- aggregate KPI/trend queries (lib/db/analytics.ts and macroservice/api.py's
-- _get_player_series both read the underlying tables the views wrap).
--
-- The view's grain is (player_id, team_id, season) -- it's built FROM
-- player_season_team, so a player rostered under two teams in the same
-- season genuinely has two view rows, with identical stat values (the
-- stats side is joined by player_id+season only, not team). An EXISTS-
-- based team filter does NOT fix this the way it does for a raw-table
-- query: EXISTS only adds a filter condition, it can't collapse rows the
-- driving table already produced -- confirmed directly (a dedicated
-- regression test, test_insights_db_integration.py, caught an EXISTS-
-- based rewrite of this exact query still returning a traded player
-- twice). SELECT DISTINCT is the correct tool here, not a workaround to
-- avoid -- it's collapsing the view's own team-membership grain down to
-- one row per player, which the view's structure requires regardless of
-- how the team filter is expressed.
--
-- The secondary `, player_id ASC` tiebreaker IS a genuine fix (independent
-- of the above): without it, whenever more players are tied on {column}
-- than fit under LIMIT, Postgres is free to return a different arbitrary
-- subset of the tied players on every call (confirmed directly). A
-- leaderboard flickering between different "#10" players on reload reads
-- as a bug users would notice, not a cosmetic non-issue.
SELECT DISTINCT player_id, player_name AS name, debut_year, last_active_year, active,
       {column} AS metric_value
FROM {view}
WHERE season = :season AND team_id = ANY(:team_ids) AND {column} IS NOT NULL
ORDER BY {column} {order}, player_id ASC
LIMIT :limit;
