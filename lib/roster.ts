/**
 * Pure roster-filtering logic shared by server (lib/db/roster.ts) and
 * client (components/analytics/PlayerSelector.tsx) code -- kept out of
 * lib/db/roster.ts specifically so importing it from a client component
 * never pulls in that file's `./client` import (@neondatabase/serverless,
 * a Node-only Postgres driver that has no business in a browser bundle).
 */

export interface RosterEntry {
  id: number;
  name: string;
  debut_year: number | null;
  last_active_year: number | null;
  active: boolean;
  positions: string[];
  is_pitcher: boolean;
  active_year_ranges: [number, number | null][];
}

/** Ported from macroservice/roster_history._active_year_ranges -- a
 * missing last_active_year means "still active" ONLY when the bio's own
 * `active` flag confirms it; a pre-lastPlayedDate-era retiree (a real data
 * gap, common for early-20th-century players) falls back to a single-
 * season span at debut rather than being projected forward indefinitely. */
export function activeYearRanges(bio: {
  debut_year: number | null;
  last_active_year: number | null;
  active: boolean;
}): [number, number | null][] {
  if (bio.debut_year === null) return [];
  if (bio.last_active_year !== null) return [[bio.debut_year, bio.last_active_year]];
  if (bio.active) return [[bio.debut_year, null]];
  return [[bio.debut_year, bio.debut_year]];
}

/** Player ids with at least one active-year span overlapping
 * [startYear, endYear] -- ported from macroservice.roster_history.
 * resolve_from_roster. `positions`, when given, keeps only players holding
 * at least one of those position acronyms (e.g. ["1B","2B","3B","SS"] for
 * Infield); omit/empty returns everyone. */
export function resolvePlayersInRange(
  roster: RosterEntry[],
  startYear: number,
  endYear: number,
  positions?: readonly string[],
): Set<number> {
  const positionSet = positions && positions.length > 0 ? new Set(positions) : null;
  const matched = new Set<number>();
  for (const entry of roster) {
    if (positionSet && !entry.positions.some((p) => positionSet.has(p))) continue;
    for (const [spanStart, spanEnd] of entry.active_year_ranges) {
      const resolvedEnd = spanEnd === null ? endYear : spanEnd;
      if (spanStart <= endYear && resolvedEnd >= startYear) {
        matched.add(entry.id);
        break;
      }
    }
  }
  return matched;
}
