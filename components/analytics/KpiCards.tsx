"use client";

import { formatStat, fullNameForMetric } from "@/lib/metrics";

export type KpiValues = Record<string, number | null>;

type KpiCardsProps = {
  metrics: [string, string][]; // [key, acronym]
  values: KpiValues | null;
};

/** Vertical KPI list -- matches pages/analytics_and_forecasts.py's current
 * layout exactly (one st.metric per row, not a horizontal row of columns;
 * see that file's history for why horizontal was dropped). */
export function KpiCards({ metrics, values }: KpiCardsProps) {
  if (!values) return null;
  return (
    <div className="flex flex-col gap-sm">
      {metrics.map(([key, acronym]) => (
        <div key={key} className="flex items-baseline justify-between border-b border-hairline pb-xs">
          <span className="text-body-sm text-steel">
            {fullNameForMetric(key)} ({acronym})
          </span>
          <span className="text-heading-5 text-ink-deep">{formatStat(values[key], key)}</span>
        </div>
      ))}
    </div>
  );
}
