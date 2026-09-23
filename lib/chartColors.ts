/**
 * Shared multi-series palette for Plotly charts. Plotly's trace/layout
 * objects don't resolve CSS custom properties, so these are literal hex
 * values mirroring the --color-* tokens in app/globals.css -- update both
 * together. Leads with Statcast teal/mint/velocity-red; MLB red is last
 * (brand color, not a primary data hue).
 */
export const CHART_PALETTE = [
  "#00a7b8", // --color-accent-blue (teal)
  "#00816a", // --color-semantic-success (deepened mint)
  "#d92c22", // --color-semantic-error (velocity red)
  "#c15a3f", // --color-accent-orange (deepened for the white background)
  "#7457a8", // --color-accent-purple (deepened)
  "#b6791a", // --color-accent-yellow (deepened)
  "#6b7280", // --color-accent-gray (deepened)
  "#bd3039", // --color-mlb-red
];

export const CHART_MARKER_OUTLINE = "#ffffff"; // --color-surface (white marker ring on the light chart background)

export function withAlpha(hex: string, alpha = 0.15): string {
  const h = hex.replace("#", "");
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}
