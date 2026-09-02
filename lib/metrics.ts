/**
 * Ported 1:1 from utils/filters.py, utils/formatters.py, macroservice/
 * players.py (headshot_url), and macroservice/roster_history.py
 * (active_years_label) -- the Streamlit app's canonical source for these.
 * Duplicated here rather than exposed via an API route since these are
 * static config/pure-formatting logic, not data that needs a round trip.
 */

export type MetricGroup = "hitting" | "pitching";

// [key, acronym] -- acronym is what leaderboard headers show.
export const HITTING_METRICS: [string, string][] = [
  ["avg", "AVG"],
  ["obp", "OBP"],
  ["slg", "SLG"],
  ["ops", "OPS"],
  ["homeRuns", "HR"],
  ["rbi", "RBI"],
  ["strikeOuts", "K"],
  ["baseOnBalls", "BB"],
  ["xba", "xBA"],
  ["avgExitVelocity", "EV"],
  ["hardHitPct", "Hard-Hit%"],
  ["barrelPct", "Barrel%"],
];

export const PITCHING_METRICS: [string, string][] = [
  ["era", "ERA"],
  ["whip", "WHIP"],
  ["strikeOuts", "K"],
  ["baseOnBalls", "BB"],
  ["inningsPitched", "IP"],
  ["earnedRuns", "ER"],
  ["cswPct", "CSW%"],
  ["whiffPct", "Whiff%"],
  ["chasePct", "Chase%"],
  ["avgVelocity", "Velo"],
];

export const METRIC_FULL_NAMES: Record<string, string> = {
  avg: "Batting Average",
  obp: "On-Base Percentage",
  slg: "Slugging Percentage",
  ops: "On-Base Plus Slugging",
  homeRuns: "Home Runs",
  rbi: "Runs Batted In",
  strikeOuts: "Strikeouts",
  baseOnBalls: "Walks",
  era: "Earned Run Average",
  whip: "Walks + Hits per Inning Pitched",
  inningsPitched: "Innings Pitched",
  earnedRuns: "Earned Runs",
  xba: "Expected Batting Average (xBA, Statcast 2015+)",
  avgExitVelocity: "Average Exit Velocity (Statcast 2015+)",
  hardHitPct: "Hard-Hit% (Statcast 2015+)",
  barrelPct: "Barrel% (Statcast 2015+)",
  cswPct: "Called Strike + Whiff % (CSW%, Statcast 2015+)",
  whiffPct: "Whiff% (Statcast 2015+)",
  chasePct: "Chase% (Statcast 2015+)",
  avgVelocity: "Average Velocity (Statcast 2015+)",
};

export function fullNameForMetric(key: string): string {
  return METRIC_FULL_NAMES[key] ?? key;
}

// Verified against the live utils.filters.RATE_METRICS set -- deliberately
// excludes avgExitVelocity/avgVelocity (see lib/db/analytics.ts's longer
// comment on why, and that this looks like an unintentional upstream
// quirk preserved for faithful parity). Used for both chart axis-splitting
// (chart.py's build_multi_metric_figure/build_forecast_figure) and
// aggregation sum-vs-mean (lib/db/analytics.ts) -- the same set serves
// both in Python too (utils.filters.is_rate_metric).
export const RATE_METRICS = new Set([
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
]);

export function isRateMetric(key: string): boolean {
  return RATE_METRICS.has(key);
}

const LEADING_ZERO_DROPPED = new Set(["avg", "obp", "slg", "ops", "xba"]);
const TWO_DECIMAL = new Set(["era", "whip", "strikeoutsPer9Inn", "walksPer9Inn", "fip"]);
const PERCENT = new Set(["hardHitPct", "barrelPct", "cswPct", "whiffPct", "chasePct"]);
const MPH = new Set(["avgExitVelocity", "avgVelocity"]);

export function formatStat(value: number | string | null | undefined, key: string): string {
  if (value === null || value === undefined || value === "") return "—";
  const num = typeof value === "number" ? value : Number(value);

  if (LEADING_ZERO_DROPPED.has(key)) {
    if (Number.isNaN(num)) return String(value);
    const text = num.toFixed(3);
    return text.startsWith("0.") ? text.slice(1) : text;
  }
  if (TWO_DECIMAL.has(key)) {
    return Number.isNaN(num) ? String(value) : num.toFixed(2);
  }
  if (PERCENT.has(key)) {
    return Number.isNaN(num) ? String(value) : `${(num * 100).toFixed(1)}%`;
  }
  if (MPH.has(key)) {
    return Number.isNaN(num) ? String(value) : `${num.toFixed(1)} mph`;
  }
  return String(value);
}

export function activeYearsLabel(
  debutYear: number | null,
  lastActiveYear: number | null,
  active: boolean,
): string {
  if (debutYear === null) return "";
  if (lastActiveYear !== null) return `${debutYear}–${lastActiveYear}`;
  if (active) return `${debutYear}–present`;
  return `${debutYear}–${debutYear}`;
}

const HEADSHOT_URL_TEMPLATE =
  "https://img.mlbstatic.com/mlb-photos/image/upload/" +
  "d_people:generic:headshot:67:current.png/w_{width},q_auto:best/" +
  "v1/people/{player_id}/headshot/67/current";

export function headshotUrl(playerId: number, width = 60): string {
  return HEADSHOT_URL_TEMPLATE.replace("{width}", String(width)).replace("{player_id}", String(playerId));
}
