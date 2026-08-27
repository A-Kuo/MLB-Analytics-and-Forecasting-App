"use client";

import { useEffect, useState } from "react";

import { getTeams, type Team } from "@/lib/api";

// Phase 1 placeholder -- the real two-panel team/player comparison,
// Aggregate KPI, Performance Trend, and Forecast sections (ported from
// pages/analytics_and_forecasts.py) land in Phase 2. This page's job here
// is just to prove the design system and the Python API wiring work.
export default function AnalyticsPage() {
  const [teams, setTeams] = useState<Team[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getTeams()
      .then(setTeams)
      .catch((err: Error) => setError(err.message));
  }, []);

  return (
    <div className="flex flex-col gap-xl">
      <div>
        <h1 className="text-heading-1">Analytics and Forecasts</h1>
        <p className="text-subtitle text-slate">
          Ported in Phase 2 -- team/player comparison, Aggregate KPI, Performance Trend, Forecast.
        </p>
      </div>
      <div className="rounded-lg border border-hairline bg-surface p-xl">
        <h2 className="text-heading-5">Backend wiring check</h2>
        {error ? (
          <p className="text-body-sm text-semantic-error">Failed to reach the API: {error}</p>
        ) : teams === null ? (
          <p className="text-body-sm text-steel">Loading teams from the Python API…</p>
        ) : (
          <p className="text-body-sm text-slate">
            Loaded {teams.length} teams from <code>/api/teams</code>.
          </p>
        )}
      </div>
    </div>
  );
}
