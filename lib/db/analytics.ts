import { query } from "./client";

type MetricConfig = { table: string; column: string; statcast: boolean };

// Ported from utils/filters.py's STATCAST_METRIC_KEYS dispatch, plus the
// camelCase (API/JS key) -> snake_case (SQL column) mapping baked into
// db/schema.sql's player_season_{hitting,pitching}_stats and
// player_statcast_{hitting,pitching}_season tables. baseOnBalls -> walks
// and strikeOuts -> strikeouts are real renames, not typos.
const HITTING_REGISTRY: Record<string, MetricConfig> = {
  avg: { table: "player_season_hitting_stats", column: "avg", statcast: false },
  obp: { table: "player_season_hitting_stats", column: "obp", statcast: false },
  slg: { table: "player_season_hitting_stats", column: "slg", statcast: false },
  ops: { table: "player_season_hitting_stats", column: "ops", statcast: false },
  homeRuns: { table: "player_season_hitting_stats", column: "home_runs", statcast: false },
  rbi: { table: "player_season_hitting_stats", column: "rbi", statcast: false },
  strikeOuts: { table: "player_season_hitting_stats", column: "strikeouts", statcast: false },
  baseOnBalls: { table: "player_season_hitting_stats", column: "walks", statcast: false },
  xba: { table: "player_statcast_hitting_season", column: "xba", statcast: true },
  avgExitVelocity: { table: "player_statcast_hitting_season", column: "avg_exit_velocity", statcast: true },
  hardHitPct: { table: "player_statcast_hitting_season", column: "hard_hit_pct", statcast: true },
  barrelPct: { table: "player_statcast_hitting_season", column: "barrel_pct", statcast: true },
};

const PITCHING_REGISTRY: Record<string, MetricConfig> = {
  era: { table: "player_season_pitching_stats", column: "era", statcast: false },
  whip: { table: "player_season_pitching_stats", column: "whip", statcast: false },
  strikeOuts: { table: "player_season_pitching_stats", column: "strikeouts", statcast: false },
  baseOnBalls: { table: "player_season_pitching_stats", column: "walks", statcast: false },
  inningsPitched: { table: "player_season_pitching_stats", column: "innings_pitched", statcast: false },
  earnedRuns: { table: "player_season_pitching_stats", column: "earned_runs", statcast: false },
  cswPct: { table: "player_statcast_pitching_season", column: "csw_pct", statcast: true },
  whiffPct: { table: "player_statcast_pitching_season", column: "whiff_pct", statcast: true },
  chasePct: { table: "player_statcast_pitching_season", column: "chase_pct", statcast: true },
  avgVelocity: { table: "player_statcast_pitching_season", column: "avg_velocity", statcast: true },
};

// Ported from utils/filters.MEAN_AGGREGATE_METRICS -- mean-aggregate
// across selected (player, year) points; everything else sums. This is
// RATE_METRICS (the chart-axis set, which keeps avgExitVelocity/
// avgVelocity off the 0-1-ish rate axis so they don't flatten against a
// .300 batting average) plus those same two metrics, since they're still
// per-player averages for aggregation purposes even though they don't
// belong on that chart axis. Originally shipped as a plain copy of
// RATE_METRICS missing those two, which meant summing a career's worth of
// exit velocity into a meaningless total (e.g. 858 "mph") -- caught via
// direct reproduction against the Neon-backed aggregate-KPI path, fixed
// upstream too (utils/filters.py).
const MEAN_AGGREGATE_METRICS = new Set([
  "avg",
  "obp",
  "slg",
  "ops",
  "era",
  "whip",
  "xba",
  "hardHitPct",
  "barrelPct",
  "cswPct",
  "whiffPct",
  "chasePct",
  "avgExitVelocity",
  "avgVelocity",
]);

function metricConfig(metricKey: string, group: "hitting" | "pitching"): MetricConfig {
  const registry = group === "pitching" ? PITCHING_REGISTRY : HITTING_REGISTRY;
  const config = registry[metricKey];
  if (!config) throw new Error(`Unknown metric '${metricKey}' for group '${group}'`);
  return config;
}

/** Single aggregate number across every (player, year) point in
 * [startYear, endYear] -- ported from utils.aggregation.aggregate_scalar,
 * done as one SQL aggregate instead of fetching every row and reducing in
 * JS. `column`/`table` are interpolated from the fixed registries above
 * (never from caller-supplied input), so this isn't a SQL-injection
 * surface despite the f-string-equivalent template literal. */
export async function getAggregateKpi(
  playerIds: readonly number[],
  metricKey: string,
  group: "hitting" | "pitching",
  startYear: number,
  endYear: number,
): Promise<number | null> {
  if (playerIds.length === 0) return null;
  const { table, column } = metricConfig(metricKey, group);
  const aggFn = MEAN_AGGREGATE_METRICS.has(metricKey) ? "AVG" : "SUM";
  const sql = `
    SELECT ${aggFn}(${column}) AS value
    FROM ${table}
    WHERE player_id = ANY($1) AND season BETWEEN $2 AND $3 AND ${column} IS NOT NULL
  `;
  const result = await query(sql, [playerIds, startYear, endYear]);
  const value = result.rows[0]?.value;
  return value === null || value === undefined ? null : Number(value);
}

/** Combined {years, values} series across every selected player -- for
 * each year that appears for at least one player, sum (counting stats) or
 * mean (rate stats) that year's values across whichever players have data
 * that year. Ported from utils.aggregation.aggregate_series, again as one
 * GROUP BY instead of a per-player fetch + JS reduce. */
export async function getAggregateSeries(
  playerIds: readonly number[],
  metricKey: string,
  group: "hitting" | "pitching",
  startYear: number,
  endYear: number,
): Promise<{ years: number[]; values: number[] }> {
  if (playerIds.length === 0) return { years: [], values: [] };
  const { table, column } = metricConfig(metricKey, group);
  const aggFn = MEAN_AGGREGATE_METRICS.has(metricKey) ? "AVG" : "SUM";
  const sql = `
    SELECT season, ${aggFn}(${column}) AS value
    FROM ${table}
    WHERE player_id = ANY($1) AND season BETWEEN $2 AND $3 AND ${column} IS NOT NULL
    GROUP BY season
    ORDER BY season
  `;
  const result = await query(sql, [playerIds, startYear, endYear]);
  return {
    years: result.rows.map((r) => r.season),
    values: result.rows.map((r) => Number(r.value)),
  };
}
