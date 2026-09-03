/**
 * Shared chart color constants for TrendChart.tsx and ForecastChart.tsx --
 * previously each hardcoded its own identical, unrelated D3/Plotly stock
 * palette (`["#1F77B4", "#D62728", ...]`). Plotly's trace/layout objects
 * don't resolve `var(--...)` CSS custom properties (they aren't a real DOM
 * style path), so these are literal hex values, each comment-linked to its
 * app/globals.css source of truth -- keep the two files in sync manually
 * when either changes.
 */

export const CHART_PALETTE = [
  "#bd3039", // --color-mlb-red (focused)
  "#518dd2", // --color-accent-blue
  "#4d9987", // --color-accent-green
  "#e8765e", // --color-accent-orange
  "#9874d2", // --color-accent-purple
  "#cc64ce", // --color-accent-pink
  "#eca438", // --color-accent-yellow
  "#e0d643", // --color-accent-lime
];

export const CHART_MARKER_OUTLINE = "#0e0e0e"; // --color-canvas-deep

export function withAlpha(hex: string, alpha = 0.15): string {
  const h = hex.replace("#", "");
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}
