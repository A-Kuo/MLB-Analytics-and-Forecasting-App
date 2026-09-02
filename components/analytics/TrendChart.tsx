"use client";

import { PlotlyChart } from "@/components/charts/PlotlyChart";
import type { AggregateSeries } from "@/lib/api";
import { isRateMetric } from "@/lib/metrics";

// Ported from chart.py's METRIC_PALETTE -- assigned in checkbox order so a
// given metric keeps its color as others are toggled on and off.
const METRIC_PALETTE = ["#1F77B4", "#D62728", "#2CA02C", "#FF7F0E", "#9467BD", "#8C564B", "#17BECF", "#E377C2"];

type TrendChartProps = {
  seriesByMetric: Record<string, AggregateSeries>;
  acronymByMetric: Record<string, string>;
  title: string;
};

/** One line per selected metric across seasons -- the React/Plotly
 * analogue of chart.py's build_multi_metric_figure. Rate stats (AVG/OPS/
 * ERA/...) and counting stats (HR/RBI/K/...) split across two y-axes so
 * the rate lines don't collapse onto the baseline next to counts in the
 * hundreds. No frame-by-frame reveal animation (a Streamlit-specific
 * touch, not essential to the chart itself). */
export function TrendChart({ seriesByMetric, acronymByMetric, title }: TrendChartProps) {
  const keys = Object.keys(seriesByMetric);
  const hasRate = keys.some((k) => isRateMetric(k));
  const hasCount = keys.some((k) => !isRateMetric(k));

  const data = keys.map((key, index) => {
    const series = seriesByMetric[key];
    const acronym = acronymByMetric[key] ?? key;
    const color = METRIC_PALETTE[index % METRIC_PALETTE.length];
    const onRateAxis = isRateMetric(key) || !hasRate;
    return {
      x: series.years,
      y: series.values,
      type: "scatter" as const,
      mode: "lines+markers" as const,
      name: acronym,
      line: { color, width: 2 },
      marker: { color, size: 7 },
      yaxis: onRateAxis ? "y" : "y2",
      hovertemplate: `%{x}<br>${acronym}: %{y}<extra></extra>`,
    };
  });

  return (
    <PlotlyChart
      data={data}
      layout={{
        title: { text: title },
        xaxis: { title: { text: "Season" }, dtick: 1 },
        yaxis: { title: { text: hasRate ? "Rate" : "Total" } },
        ...(hasRate && hasCount ? { yaxis2: { title: { text: "Total" }, overlaying: "y", side: "right" } } : {}),
        template: "plotly_dark",
        hovermode: "x unified",
        margin: { t: 56, b: 40, l: 48, r: 48 },
        paper_bgcolor: "transparent",
        plot_bgcolor: "transparent",
        autosize: true,
      }}
      useResizeHandler
      style={{ width: "100%", height: "400px" }}
      config={{ responsive: true, displayModeBar: false }}
    />
  );
}
