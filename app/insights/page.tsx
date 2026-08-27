"use client";

import { useEffect, useState } from "react";

import { getHealth } from "@/lib/api";

// Phase 1 placeholder -- the real team selector and per-metric season
// leaderboards (ported from pages/insights.py) land in Phase 3.
export default function InsightsPage() {
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getHealth()
      .then((health) => setStatus(health.status))
      .catch((err: Error) => setError(err.message));
  }, []);

  return (
    <div className="flex flex-col gap-xl">
      <div>
        <h1 className="text-heading-1">Insights</h1>
        <p className="text-subtitle text-slate">
          Ported in Phase 3 -- team selector and season leaderboards by metric.
        </p>
      </div>
      <div className="rounded-lg border border-hairline bg-surface p-xl">
        <h2 className="text-heading-5">Backend wiring check</h2>
        {error ? (
          <p className="text-body-sm text-semantic-error">Failed to reach the API: {error}</p>
        ) : status === null ? (
          <p className="text-body-sm text-steel">Checking /api/health…</p>
        ) : (
          <p className="text-body-sm text-slate">
            <code>/api/health</code> responded: {status}
          </p>
        )}
      </div>
    </div>
  );
}
