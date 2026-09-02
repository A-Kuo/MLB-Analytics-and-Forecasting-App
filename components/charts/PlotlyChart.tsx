"use client";

import dynamic from "next/dynamic";
import type { ComponentType } from "react";
import type { PlotParams } from "react-plotly.js";

// plotly.js-dist-min (not the full plotly.js) keeps the client bundle
// reasonable -- react-plotly.js's default export assumes the full
// package, so it's wired through the factory instead. Plotly touches
// `window`/canvas directly and cannot run during SSR/static generation,
// hence the dynamic import with ssr: false.
const Plot = dynamic(
  () =>
    Promise.all([import("react-plotly.js/factory"), import("plotly.js-dist-min")]).then(
      ([{ default: createPlotlyComponent }, Plotly]) => createPlotlyComponent(Plotly.default ?? Plotly),
    ) as unknown as Promise<{ default: ComponentType<PlotParams> }>,
  { ssr: false },
);

export function PlotlyChart(props: PlotParams) {
  return <Plot {...props} />;
}
