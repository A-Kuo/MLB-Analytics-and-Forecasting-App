/**
 * Typed fetch wrapper for the Python backend (macroservice/api.py),
 * deployed as a Vercel Python Function at /api/* (see vercel.json).
 * Phase 1 only needs health + teams to prove the wiring works end to
 * end -- the rest of client.py's surface (aggregate KPI/series/forecast,
 * insights leaderboards, team news) gets its own routes added in the
 * phase that actually needs them.
 */

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

export function getTeams(): Promise<Team[]> {
  return apiFetch("/teams");
}
