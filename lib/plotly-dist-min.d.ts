// plotly.js-dist-min ships no type declarations of its own -- it's the
// same runtime API as plotly.js (which @types/plotly.js already covers
// via react-plotly.js's own dependency), so re-point at that.
declare module "plotly.js-dist-min" {
  import * as Plotly from "plotly.js";
  export = Plotly;
}
