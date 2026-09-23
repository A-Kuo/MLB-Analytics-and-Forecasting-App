/**
 * Shared multi-series palette for Plotly charts. Plotly's trace/layout
 * objects don't resolve CSS custom properties, so these are literal hex
 * values mirroring the --color-* tokens in app/globals.css -- update both
 * together. Leads with Statcast teal/mint/velocity-red; MLB red is last
 * (brand color, not a primary data hue).
 */
export const CHART_PALETTE = [
  "#00f0ff", // --color-accent-blue (Statcast Teal)
  "#00c896", // --color-accent-blue-base (Data Mint)
  "#ff3b30", // --color-semantic-error (Velocity Red)
  "#e8765e", // --color-accent-orange
  "#9874d2", // --color-accent-purple
  "#eca438", // --color-accent-yellow
  "#888888", // --color-accent-gray
  "#bd3039", // --color-mlb-red
];

export const CHART_MARKER_OUTLINE = "#05070c"; // --color-canvas-deep

export function withAlpha(hex: string, alpha = 0.15): string {
  const h = hex.replace("#", "");
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}
