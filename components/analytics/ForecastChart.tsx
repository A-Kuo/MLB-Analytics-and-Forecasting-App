"use client";

import { PlotlyChart } from "@/components/charts/PlotlyChart";
import type { ForecastPayload } from "@/lib/api";
import { isRateMetric } from "@/lib/metrics";

const METRIC_PALETTE = ["#1F77B4", "#D62728", "#2CA02C", "#FF7F0E", "#9467BD", "#8C564B", "#17BECF", "#E377C2"];

function translucent(hex: string, alpha = 0.15): string {
  const h = hex.replace("#", "");
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

type ForecastChartProps = {
  forecastByMetric: Record<string, ForecastPayload>;
  acronymByMetric: Record<string, string>;
  title: string;
};

/** Per selected metric: a shaded 95% CI band, a dotted forecast trend line
 * spanning [train_end, forecast_end], and diamond markers wherever real
 * ground truth exists in that window -- the React/Plotly analogue of
 * chart.py's build_forecast_figure. Same dual-axis rate/count split as
 * TrendChart. No frame-by-frame reveal animation. */
export function ForecastChart({ forecastByMetric, acronymByMetric, title }: ForecastChartProps) {
  const keys = Object.keys(forecastByMetric);
  const hasRate = keys.some((k) => isRateMetric(k));
  const hasCount = keys.some((k) => !isRateMetric(k));

  const data: Record<string, unknown>[] = [];
  keys.forEach((key, index) => {
    const payload = forecastByMetric[key];
    const acronym = acronymByMetric[key] ?? key;
    const color = METRIC_PALETTE[index % METRIC_PALETTE.length];
    const axis = isRateMetric(key) || !hasRate ? "y" : "y2";
    const { years, forecast, ci_lower, ci_upper, actual } = payload;

    if (years.length > 0) {
      data.push({
        x: [...years, ...years.slice().reverse()],
        y: [...ci_upper, ...ci_lower.slice().reverse()],
        fill: "toself",
        fillcolor: translucent(color),
        line: { width: 0 },
        yaxis: axis,
        name: `${acronym} 95% CI`,
        hoverinfo: "skip",
        showlegend: false,
      });
    }

    data.push({
      x: years,
      y: forecast,
      type: "scatter",
      mode: "lines",
      name: `${acronym} forecast`,
      line: { color, dash: "dot", width: 2 },
      yaxis: axis,
      hoverinfo: "skip",
    });

    const actualYears = years.filter((_, i) => actual[i] !== null);
    const actualValues = actual.filter((v) => v !== null);
    if (actualYears.length > 0) {
      data.push({
        x: actualYears,
        y: actualValues,
        type: "scatter",
        mode: "markers",
        name: `${acronym} actual`,
        marker: { color, size: 9, symbol: "diamond", line: { width: 1, color: "#333" } },
        yaxis: axis,
        hovertemplate: `%{x}<br>${acronym}: %{y}<extra></extra>`,
      });
    }
  });

  return (
    <PlotlyChart
      data={data as never}
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
