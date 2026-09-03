-- Thin, domain-named wrapper over v_player_season_hitting_metrics for the
-- Insights leaderboard specifically -- same underlying join (kept as one
-- source of truth), just a name that matches its consumer
-- (macroservice/insights_db.py's top_players_by_metric, group="hitting").
CREATE OR REPLACE VIEW v_insights_hitting AS
SELECT * FROM v_player_season_hitting_metrics;
