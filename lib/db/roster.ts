import { activeYearRanges, type RosterEntry } from "@/lib/roster";
import { query } from "./client";

export type { RosterEntry };

/** All-time roster for one team, enriched with active-year spans -- the
 * Node/Postgres-native equivalent of client.get_team_roster_with_active_years
 * (roster_stints + players, see macroservice/roster_history_db.py). No
 * live-API fallback here: roster_stints is populated by the scheduled
 * scripts/backfill_roster_history.py job, matching how Insights leans on
 * its own backfill rather than a per-request live path. */
export async function getTeamRosterWithActiveYears(teamId: number): Promise<RosterEntry[]> {
  const result = await query(
    `
    SELECT p.id::int AS id, p.name, p.debut_year, p.last_active_year, p.active,
           rs.positions, rs.is_pitcher
    FROM roster_stints rs
    JOIN players p ON p.id = rs.player_id
    WHERE rs.team_id = $1
    `,
    [teamId],
  );
  return result.rows.map((row) => ({
    ...row,
    active_year_ranges: activeYearRanges(row),
  }));
}
