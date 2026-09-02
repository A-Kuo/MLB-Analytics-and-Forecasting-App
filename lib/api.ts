/**
 * Typed fetch wrapper for this app's own Next.js API routes (app/api/*),
 * which query Neon directly via lib/db/* (see lib/db/client.ts --
 * @neondatabase/serverless, Neon's own HTTP-based driver, a better fit for
 * Vercel's serverless model than a pooled TCP connection). The Python
 * function (macroservice/api.py, routed by vercel.json) is a separate,
 * still-real thing -- it's what the heavier compute (regression/forecast
 * fitting, Statcast processing) will eventually route through -- but
 * teams/news/insights-leaderboard are plain Postgres reads that already
 * have a working, Vercel-native implementation here, so this module talks
 * to that rather than duplicating the same three reads through Python too.
 */

// Mirrors macroservice/teams.py's TEAM_NEWS_HUB_SLUGS -- duplicated here
// (rather than round-tripping through Python) since lib/db/teams.ts reads
// teams.json directly and has no news_hub_url field of its own. Falls back
// to GENERAL_NEWS_HUB_URL for any id not listed, matching
// teams.team_news_hub_url's own fallback exactly.
const TEAM_NEWS_HUB_SLUGS: Record<number, string> = {
  108: "angels",
  109: "dbacks",
  110: "orioles",
  111: "redsox",
  112: "cubs",
  113: "reds",
  114: "guardians",
  115: "rockies",
  116: "tigers",
  117: "astros",
  118: "royals",
  119: "dodgers",
  120: "nationals",
  121: "mets",
  133: "athletics",
  134: "pirates",
  135: "padres",
  136: "mariners",
  137: "giants",
  138: "cardinals",
  139: "rays",
  140: "rangers",
  141: "bluejays",
  142: "twins",
  143: "phillies",
  144: "braves",
  145: "whitesox",
  146: "marlins",
  147: "yankees",
  158: "brewers",
};

export const GENERAL_NEWS_HUB_URL = "https://www.mlb.com/news";

export function teamNewsHubUrl(teamId: number): string {
  const slug = TEAM_NEWS_HUB_SLUGS[teamId];
  return slug ? `https://www.mlb.com/${slug}/news` : GENERAL_NEWS_HUB_URL;
}

export interface Team {
  id: number;
  name: string;
  abbreviation: string;
  city: string;
  nickname: string;
  primary_color: string;
  logo_url: string;
  keywords: string[];
  league: string;
  division: string;
}

export interface LeaderboardRow {
  player_id: number;
  name: string;
  debut_year: number | null;
  last_active_year: number | null;
  active: boolean;
  metric_value: number | string | null;
}

export interface NewsItem {
  id: string;
  headline: string;
  source: string;
  url: string;
  thumbnail_url: string | null;
  published_at: string | null;
}

async function apiFetch<T>(path: string): Promise<T> {
  const res = await fetch(`/api${path}`);
  if (!res.ok) {
    throw new Error(`API request failed: ${path} (${res.status})`);
  }
  return res.json() as Promise<T>;
}

export function getHealth(): Promise<{ status: string }> {
  return apiFetch("/health");
}

export async function getTeams(): Promise<Team[]> {
  const { data } = await apiFetch<{ data: Team[] }>("/teams");
  return data;
}

export async function getInsightsLeaderboard(
  metricKey: string,
  group: "hitting" | "pitching",
  season: number,
  teamIds: readonly number[],
  limit = 10,
): Promise<LeaderboardRow[]> {
  const params = new URLSearchParams({
    metric: metricKey,
    group,
    season: String(season),
    teamIds: teamIds.join(","),
    limit: String(limit),
  });
  const { data } = await apiFetch<{ data: LeaderboardRow[] }>(`/insights?${params}`);
  return data;
}

export async function getTeamNews(
  teamIds: readonly number[],
  days = 7,
  limit = 10,
): Promise<NewsItem[]> {
  if (teamIds.length === 0) return [];
  const params = new URLSearchParams({ teamIds: teamIds.join(","), days: String(days), limit: String(limit) });
  const { data } = await apiFetch<{ data: NewsItem[] }>(`/news?${params}`);
  return data;
}
