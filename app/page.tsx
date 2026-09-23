import Link from "next/link";

// Architecture layers -- the data-engineering / analytics / ML+UI "sandwich"
// also described in README.md's Project Architecture section.
const LAYERS: { title: string; body: string }[] = [
  {
    title: "Data engineering",
    body:
      "Scheduled GitHub Actions jobs pull rosters, season stats, Statcast telemetry, and team news from the MLB Stats API, Baseball Savant, and RSS/Atom feeds, then write them into Neon Postgres through idempotent upserts -- reruns never duplicate rows.",
  },
  {
    title: "Analytics",
    body:
      "A metric registry and position-aware taxonomy keep hitting and pitching separate and apply the right aggregation rule per stat -- counting stats sum across a cohort, rate stats average -- so multi-player comparisons stay statistically meaningful.",
  },
  {
    title: "Forecasting & UI",
    body:
      "Rolling features feed a walk-forward-validated regression zoo, and the Next.js frontend (backed by the same Postgres data) renders the results as leaderboards, trend charts, and forecast bands with confidence intervals.",
  },
];

const MODELS: { name: string; role: string }[] = [
  { name: "Ridge", role: "Regularized linear baseline -- stable when rolling features are collinear." },
  { name: "Huber", role: "Robust to the heavy-tailed noise of slumps and outlier games." },
  { name: "SVR (RBF)", role: "Captures non-linear fatigue curves without a fixed parametric shape." },
  { name: "Gaussian Process", role: "The only model with native uncertainty -- produces the forecast's confidence band." },
  { name: "Random Forest", role: "Tree-based baseline for interaction effects (rest days, home/away)." },
  { name: "HistGradientBoosting", role: "A second, faster-fitting tree-based baseline for the same interactions." },
];

export default function HomePage() {
  return (
    <div className="mx-auto flex max-w-[900px] flex-col gap-section px-6 py-xl">
      <section className="flex flex-col gap-md py-lg text-center">
        <h1 className="text-heading-1 text-ink-deep">MLB Analytics &amp; Forecasting Platform</h1>
        <p className="text-subtitle text-slate">
          An end-to-end platform that turns raw MLB and Statcast telemetry into interactive leaderboards, trend
          analysis, and leakage-free performance forecasts -- not just a dashboard over a live API.
        </p>
        <div className="flex flex-wrap items-center justify-center gap-sm pt-xs">
          <Link
            href="/insights"
            className="rounded-full bg-accent-blue px-5 py-2.5 text-body-sm-medium text-white transition-colors duration-(--duration-xs) ease-(--ease-primary) hover:bg-accent-blue-base"
          >
            Explore Insights
          </Link>
          <Link
            href="/analytics"
            className="rounded-full border border-hairline-strong px-5 py-2.5 text-body-sm-medium text-ink transition-colors duration-(--duration-xs) ease-(--ease-primary) hover:bg-surface-soft"
          >
            Analytics &amp; Forecasts
          </Link>
        </div>
      </section>

      <section className="flex flex-col gap-sm">
        <h2 className="text-heading-3 text-ink-deep">What this is</h2>
        <p className="text-body-md text-ink">
          Most personal sports-analytics projects pick one of two shortcuts: a dashboard that calls a live,
          rate-limited public API on every click, or a clean model trained in a notebook with no pipeline or
          interface behind it. This project bridges both halves -- a cache-aware Postgres data mart decouples slow,
          heterogeneous data acquisition from the interactive layer, so leaderboards and charts stay fast while the
          forecasting side stays methodologically honest: chronological validation, an evaluated model zoo, and a
          real confidence interval instead of a single point guess.
        </p>
      </section>

      <section className="flex flex-col gap-md">
        <h2 className="text-heading-3 text-ink-deep">System architecture</h2>
        <p className="text-body-md text-ink">
          The app is built in three layers, each independent of how the others are consumed -- the same Postgres
          data mart serves both the legacy Streamlit prototype and this Next.js frontend.
        </p>
        <div className="grid gap-sm sm:grid-cols-3">
          {LAYERS.map((layer) => (
            <div key={layer.title} className="rounded-md border border-hairline bg-surface p-md">
              <h3 className="mb-xs text-heading-5 text-ink-deep">{layer.title}</h3>
              <p className="text-body-sm text-steel">{layer.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="flex flex-col gap-sm">
        <h2 className="text-heading-3 text-ink-deep">Stats &amp; telemetry</h2>
        <p className="text-body-md text-ink">
          Standard box-score stats come from the MLB Stats API; pitch- and batted-ball-level telemetry -- exit
          velocity, launch angle, expected batting average, hard-hit rate, whiff and chase rate, pitch velocity --
          comes from Baseball Savant&apos;s Statcast data (available from 2015 onward). Both feed a rolling-window
          transform: a trailing average smooths game-to-game noise into a time-dependent target, and a shorter
          rolling window over that target becomes a momentum feature, alongside rest days, home/away context, and
          the Statcast fields above as the supervised feature vector.
        </p>
      </section>

      <section className="flex flex-col gap-md">
        <h2 className="text-heading-3 text-ink-deep">Predictive modeling &amp; forecasting</h2>
        <p className="text-body-md text-ink">
          Forecasts are validated with <code className="text-body-sm-medium text-accent-blue">TimeSeriesSplit</code>{" "}
          walk-forward cross-validation, not a random train/test split -- each fold trains only on data available
          before the window it&apos;s scored against, so no future performance leaks into a historical prediction.
          Six candidate regressors are evaluated per player, chosen for distinct bias-variance trade-offs rather than
          picked by default:
        </p>
        <div className="grid gap-xs sm:grid-cols-2">
          {MODELS.map((m) => (
            <div key={m.name} className="flex items-baseline gap-sm border-b border-hairline pb-xs">
              <span className="w-36 flex-none text-body-sm-medium text-ink-deep">{m.name}</span>
              <span className="text-body-sm text-steel">{m.role}</span>
            </div>
          ))}
        </div>
        <p className="text-body-md text-ink">
          The Gaussian Process model is what makes the forecast band on the Analytics page real rather than
          decorative: its predictive standard deviation (σ) produces an approximate 90% interval (μ ± 1.645σ)
          around the trajectory, and performance across all six candidates is reported as R², RMSE, and MAE
          together rather than any single metric.
        </p>
      </section>

      <section className="flex flex-col gap-sm">
        <h2 className="text-heading-3 text-ink-deep">Postgres as a data mart</h2>
        <p className="text-body-md text-ink">
          Neon Postgres holds a curated, relational data mart -- player biographies, roster history,
          team-season membership, season stats, Statcast aggregates, leaderboard inputs, and team news -- rather
          than a raw copy of every upstream API response. Writes go through <code className="text-body-sm-medium text-accent-blue">ON CONFLICT</code>{" "}
          upserts, so a rerun of a backfill or ingestion job is always safe. Reads are Postgres-first with a
          controlled live-API fallback where that makes sense (a single player&apos;s roster history); leaderboards
          and team news skip the fallback entirely, since a live call for a 30-team, 20-metric leaderboard would mean
          thousands of nested API requests on a single page load. Versioned SQL lives in{" "}
          <code className="text-body-sm-medium text-accent-blue">db/migrations</code>,{" "}
          <code className="text-body-sm-medium text-accent-blue">db/queries</code>, and{" "}
          <code className="text-body-sm-medium text-accent-blue">db/views</code> rather than embedded in application
          code.
        </p>
      </section>

      <section className="flex flex-col gap-sm">
        <h2 className="text-heading-3 text-ink-deep">Next.js frontend</h2>
        <p className="text-body-md text-ink">
          This frontend is a phased rewrite of the original Streamlit app onto Next.js&apos;s App Router, deployed on
          Vercel. Route handlers under <code className="text-body-sm-medium text-accent-blue">app/api</code> query
          Neon directly through its serverless HTTP driver rather than a pooled TCP connection -- a better fit for
          Vercel&apos;s stateless functions -- while the heavier regression fitting still routes through the Python
          FastAPI service. The interface itself favors letting the underlying data drive layout decisions: sections
          fold away when their results aren&apos;t needed, controls sit beside results instead of stacking above
          them on wide screens, and a live scoreboard strip reflects today&apos;s games without leaving the page.
        </p>
      </section>
    </div>
  );
}
