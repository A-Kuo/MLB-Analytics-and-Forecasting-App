-- Batch-scored outputs from the offline PyTorch team-forecast pipeline
-- (notebooks/*_smoke.ipynb locally, notebooks/kaggle/*/*.ipynb on Kaggle's
-- GPUs -- see scripts/load_team_forecasts.py). The models themselves are
-- never stored here, only their outputs: Streamlit reads these tables and
-- never trains anything. `model_version` is the shared key across all four
-- tables, matching the results JSON's own `model_version` field verbatim,
-- so a given notebook run's predictions/holdout/metrics can always be
-- traced back to the exact run and code state (hyperparameters, git_commit)
-- that produced them.
CREATE TABLE IF NOT EXISTS team_forecast_runs (
    model_version        TEXT PRIMARY KEY,
    track                TEXT NOT NULL,             -- 'season_aggregate' | 'statcast_era'
    run_timestamp         TIMESTAMPTZ NOT NULL,
    environment           TEXT NOT NULL,             -- 'kaggle_gpu' | 'local_smoke'
    training_start_year   INTEGER NOT NULL,
    training_end_year     INTEGER NOT NULL,
    holdout_start_year    INTEGER NOT NULL,
    holdout_end_year      INTEGER NOT NULL,
    hyperparameters       JSONB,
    -- Exactly one active run per track at a time -- client.py always
    -- filters on track plus this flag, so "which run is current" never
    -- depends on a timestamp sort. Older runs stay in the table (not
    -- deleted) so past runs remain comparable; enforced by the loader
    -- script's transaction, not a DB constraint (Postgres has no native
    -- "at most one TRUE per group" constraint without a partial unique
    -- index, which felt like more machinery than this needs).
    is_active             BOOLEAN NOT NULL DEFAULT FALSE,
    notes                 TEXT
);

CREATE TABLE IF NOT EXISTS team_forecast_holdout (
    model_version TEXT NOT NULL REFERENCES team_forecast_runs(model_version),
    team_id       INTEGER NOT NULL,
    year          INTEGER NOT NULL,
    metric        TEXT NOT NULL,
    actual        DOUBLE PRECISION,   -- NULL when the real value isn't known/available for this team-year
    predicted     DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (model_version, team_id, year, metric)
);

CREATE TABLE IF NOT EXISTS team_forecast_predictions (
    model_version TEXT NOT NULL REFERENCES team_forecast_runs(model_version),
    team_id       INTEGER NOT NULL,
    year          INTEGER NOT NULL,
    metric        TEXT NOT NULL,
    predicted     DOUBLE PRECISION NOT NULL,
    ci_lower      DOUBLE PRECISION,   -- NULL until a model produces real uncertainty bounds
    ci_upper      DOUBLE PRECISION,
    PRIMARY KEY (model_version, team_id, year, metric)
);

CREATE TABLE IF NOT EXISTS team_forecast_metrics (
    model_version TEXT NOT NULL REFERENCES team_forecast_runs(model_version),
    metric        TEXT NOT NULL,
    holdout_r2    DOUBLE PRECISION,
    holdout_rmse  DOUBLE PRECISION,
    n_holdout     INTEGER,
    PRIMARY KEY (model_version, metric)
);
