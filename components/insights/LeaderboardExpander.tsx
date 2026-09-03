"use client";

import Image from "next/image";
import { useEffect, useState } from "react";

import { getInsightsLeaderboard, type LeaderboardRow } from "@/lib/api";
import { activeYearsLabel, formatStat, fullNameForMetric, headshotUrl, type MetricGroup } from "@/lib/metrics";

type LeaderboardExpanderProps = {
  metricKey: string;
  acronym: string;
  group: MetricGroup;
  season: number;
  teamIds: readonly number[];
  limit?: number;
};

/**
 * One collapsible leaderboard, matching pages/insights.py's
 * _render_leaderboard exactly: the query always runs (an <expander>'s body
 * executes in Streamlit whether or not it's visually open), and coverage
 * gaps name the exact backfill command to run rather than looking like a
 * bug. Collapsed by default here purely for display -- ~22 of these render
 * per group, and Streamlit's own expanders default closed too.
 */
export function LeaderboardExpander({
  metricKey,
  acronym,
  group,
  season,
  teamIds,
  limit = 10,
}: LeaderboardExpanderProps) {
  const [open, setOpen] = useState(false);
  const [rows, setRows] = useState<LeaderboardRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (teamIds.length === 0) {
      setRows(null);
      return;
    }
    setLoading(true);
    setError(null);
    getInsightsLeaderboard(metricKey, group, season, teamIds, limit)
      .then(setRows)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
    // teamIds is joined so the effect only re-fires on a real membership
    // change, not a new-but-equal array reference from the parent re-render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [metricKey, group, season, teamIds.join(",")]);

  return (
    <div className="rounded-md border border-hairline">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between px-md py-sm text-left text-body-sm-medium text-ink transition-colors duration-(--duration-xs) ease-(--ease-primary) hover:bg-surface-soft"
      >
        <span>
          {fullNameForMetric(metricKey)} ({acronym})
        </span>
        <span className="text-steel">{open ? "▾" : "▸"}</span>
      </button>

      {open && (
        <div className="border-t border-hairline p-md">
          {teamIds.length === 0 ? (
            <p className="text-body-sm text-stone">Select at least one team.</p>
          ) : error ? (
            <p className="text-body-sm text-semantic-error">
              Couldn&apos;t reach the leaderboard database.
            </p>
          ) : loading || rows === null ? (
            <p className="text-body-sm text-stone">Loading…</p>
          ) : rows.length === 0 ? (
            <p className="text-body-sm text-stone">
              No cached data for {season} among the selected teams yet. Run:
              <br />
              <code>python scripts/backfill_season_leaderboard.py --season {season}</code>
            </p>
          ) : (
            <ol className="flex flex-col gap-xs">
              {rows.map((row, i) => {
                const years = activeYearsLabel(row.debut_year, row.last_active_year, row.active);
                return (
                  <li key={row.player_id} className="flex items-center gap-sm text-body-sm text-ink">
                    <span className="w-8 text-steel">#{i + 1}</span>
                    <Image
                      src={headshotUrl(row.player_id, 60)}
                      alt=""
                      width={32}
                      height={32}
                      unoptimized
                      className="rounded-full"
                    />
                    <span className="flex-1 truncate">
                      {row.name}
                      {years ? ` (${years})` : ""}
                    </span>
                    <span className="font-medium">{formatStat(row.metric_value, metricKey)}</span>
                  </li>
                );
              })}
            </ol>
          )}
        </div>
      )}
    </div>
  );
}
