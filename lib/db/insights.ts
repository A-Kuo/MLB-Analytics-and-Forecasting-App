import { query } from "./client";

const HITTING_METRICS: Record<string, { table: string; column: string; ascending: boolean }> = {
  avg: { table: "player_season_hitting_stats", column: "avg", ascending: false },
  obp: { table: "player_season_hitting_stats", column: "obp", ascending: false },
  slg: { table: "player_season_hitting_stats", column: "slg", ascending: false },
  ops: { table: "player_season_hitting_stats", column: "ops", ascending: false },
  homeRuns: { table: "player_season_hitting_stats", column: "home_runs", ascending: false },
  rbi: { table: "player_season_hitting_stats", column: "rbi", ascending: false },
  strikeOuts: { table: "player_season_hitting_stats", column: "strikeouts", ascending: false },
  baseOnBalls: { table: "player_season_hitting_stats", column: "walks", ascending: false },
  xba: { table: "player_statcast_hitting_season", column: "xba", ascending: false },
  avgExitVelocity: { table: "player_statcast_hitting_season", column: "avg_exit_velocity", ascending: false },
  hardHitPct: { table: "player_statcast_hitting_season", column: "hard_hit_pct", ascending: false },
  barrelPct: { table: "player_statcast_hitting_season", column: "barrel_pct", ascending: false },
};

const PITCHING_METRICS: Record<string, { table: string; column: string; ascending: boolean }> = {
  era: { table: "player_season_pitching_stats", column: "era", ascending: true },
  whip: { table: "player_season_pitching_stats", column: "whip", ascending: true },
  strikeOuts: { table: "player_season_pitching_stats", column: "strikeouts", ascending: false },
  baseOnBalls: { table: "player_season_pitching_stats", column: "walks", ascending: true },
  inningsPitched: { table: "player_season_pitching_stats", column: "innings_pitched", ascending: false },
  earnedRuns: { table: "player_season_pitching_stats", column: "earned_runs", ascending: true },
  cswPct: { table: "player_statcast_pitching_season", column: "csw_pct", ascending: false },
  whiffPct: { table: "player_statcast_pitching_season", column: "whiff_pct", ascending: false },
  chasePct: { table: "player_statcast_pitching_season", column: "chase_pct", ascending: false },
  avgVelocity: { table: "player_statcast_pitching_season", column: "avg_velocity", ascending: false },
};

export async function getInsightsLeaderboard(metricKey: string, group: string, season: number, teamIds: number[], limit = 10) {
  const registry = group === "pitching" ? PITCHING_METRICS : HITTING_METRICS;
  const metricConfig = registry[metricKey];

  if (!metricConfig) {
    throw new Error(`Invalid metric: ${metricKey} for group: ${group}`);
  }

  const { table, column, ascending } = metricConfig;
  const order = ascending ? "ASC" : "DESC";

  // Use string concatenation for table and column, which is safe since we got them from our own registry.
  //
  // Team membership is filtered via EXISTS against player_season_team, not
  // a JOIN + SELECT DISTINCT: a player traded between two selected teams
  // has two membership rows for the same season, so a plain JOIN
  // multiplies the outer row (same metric_value twice) and needs
  // DISTINCT to clean up after -- forcing Postgres to sort+dedupe the
  // whole result before LIMIT can apply. EXISTS is a semi-join (just
  // "does a qualifying row exist"), so there's nothing to deduplicate.
  //
  // The secondary `p.id ASC` tiebreaker is a real bug fix: without it,
  // whenever more players are tied on the metric than fit under LIMIT,
  // Postgres can return a different arbitrary subset of the tied players
  // on every call (confirmed directly against this exact query) -- a
  // leaderboard flickering between different "#10" players on reload.
  const sql = `
    SELECT p.id::int AS player_id, p.name, p.debut_year, p.last_active_year, p.active,
           m.${column} AS metric_value
    FROM ${table} m
    JOIN players p ON p.id = m.player_id
    WHERE m.season = $1 AND m.${column} IS NOT NULL
      AND EXISTS (
        SELECT 1 FROM player_season_team pst
        WHERE pst.player_id = m.player_id AND pst.season = m.season AND pst.team_id = ANY($2)
      )
    ORDER BY m.${column} ${order}, p.id ASC
    LIMIT $3
  `;

  const result = await query(sql, [season, teamIds, limit]);
  return result.rows;
}
