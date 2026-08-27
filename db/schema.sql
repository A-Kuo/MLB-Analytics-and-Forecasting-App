-- Postgres cache for every domain this app caches in its Neon instance:
-- roster/bio data (macroservice/roster_history_db.py), batch-scored
-- PyTorch team forecasts (scripts/load_team_forecasts.py), and season
-- stats/Statcast/game logs (macroservice/season_stats_db.py).
--
-- Applied idempotently by macroservice.db.ensure_schema() on every
-- backfill/load run, so this file is the single source of truth for the
-- schema across all of them -- there is no separate migration tool.
-- Future changes append ALTER TABLE ... IF NOT EXISTS statements here
-- rather than being managed as versioned migrations; the scope (one
-- writer per domain, changes a few times a year at most) doesn't justify
-- Alembic.

CREATE TABLE IF NOT EXISTS players (
    id                BIGINT PRIMARY KEY,        -- MLB person id, the same id used throughout the app
    name              TEXT NOT NULL,
    debut_year        INTEGER,                   -- NULL means "unknown" (a real data gap), not "no debut"
    -- NULL is ambiguous on its own: it means either "still playing" or
    -- "retired, but the API never recorded a last-played date". The
    -- `active` flag below disambiguates -- see _active_year_ranges in
    -- macroservice/roster_history.py, which owns that interpretation.
    last_active_year  INTEGER,
    active            BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS roster_stints (
    team_id     INTEGER NOT NULL,
    player_id   BIGINT NOT NULL REFERENCES players(id),
    -- Usually one element; three when a generic "OF" entry was normalized
    -- to LF/CF/RF (see get_alltime_roster). Array rather than a join table
    -- because the only query is a set-overlap test, which maps to `&&`.
    positions   TEXT[] NOT NULL,
    is_pitcher  BOOLEAN NOT NULL DEFAULT FALSE,
    -- team_id leads deliberately: the PK index then already serves the
    -- only read pattern ("this team's whole roster"), no extra index needed.
    PRIMARY KEY (team_id, player_id)
);

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

-- Season stats, Statcast season aggregates, and game logs (see
-- macroservice/season_stats_db.py). Lazy, self-healing caches -- populated
-- as the dashboard is actually used, not backfilled -- and only ever
-- written for a season once it's confirmed complete (client.py's
-- freshness split): the current in-progress season always bypasses these
-- tables and hits the live API directly, since these stats change every
-- game. Column sets match exactly what utils/filters.py's
-- HITTING_METRICS/PITCHING_METRICS (plain-API subset) and
-- GAME_LOG_COLUMNS already define -- the fields this app actually reads,
-- not the full raw API response.

CREATE TABLE IF NOT EXISTS player_season_hitting_stats (
    player_id  BIGINT NOT NULL,
    season     INTEGER NOT NULL,
    avg        DOUBLE PRECISION,
    obp        DOUBLE PRECISION,
    slg        DOUBLE PRECISION,
    ops        DOUBLE PRECISION,
    home_runs  INTEGER,
    rbi        INTEGER,
    strikeouts INTEGER,
    walks      INTEGER,
    PRIMARY KEY (player_id, season)
);

CREATE TABLE IF NOT EXISTS player_season_pitching_stats (
    player_id        BIGINT NOT NULL,
    season           INTEGER NOT NULL,
    era              DOUBLE PRECISION,
    whip             DOUBLE PRECISION,
    strikeouts       INTEGER,
    walks            INTEGER,
    -- Stored as float(raw): the API's "182.1" thirds-notation (182 and 1/3
    -- innings) already gets parsed as naive decimal by the live path
    -- (players.get_season_series) -- this preserves that existing
    -- behavior rather than fixing an unrelated pre-existing quirk here.
    innings_pitched  DOUBLE PRECISION,
    earned_runs      INTEGER,
    PRIMARY KEY (player_id, season)
);

CREATE TABLE IF NOT EXISTS player_statcast_hitting_season (
    player_id         BIGINT NOT NULL,
    season            INTEGER NOT NULL,
    xba               DOUBLE PRECISION,
    avg_exit_velocity DOUBLE PRECISION,
    hard_hit_pct      DOUBLE PRECISION,
    barrel_pct        DOUBLE PRECISION,
    PRIMARY KEY (player_id, season)
);

CREATE TABLE IF NOT EXISTS player_statcast_pitching_season (
    player_id    BIGINT NOT NULL,
    season       INTEGER NOT NULL,
    csw_pct      DOUBLE PRECISION,
    whiff_pct    DOUBLE PRECISION,
    chase_pct    DOUBLE PRECISION,
    avg_velocity DOUBLE PRECISION,
    PRIMARY KEY (player_id, season)
);

-- game_index disambiguates true doubleheaders (two games, same date) --
-- a fallback tiebreaker, not a verified real game id; see
-- macroservice/season_stats_db.py's _dedupe_game_index for where this
-- gets computed, and the plan's execution notes on verifying whether the
-- API exposes a real per-game id (e.g. a nested game.gamePk) that would
-- make a cleaner PK than this.
CREATE TABLE IF NOT EXISTS player_game_log_hitting (
    player_id   BIGINT NOT NULL,
    season      INTEGER NOT NULL,
    game_date   DATE NOT NULL,
    game_index  SMALLINT NOT NULL DEFAULT 0,
    opponent    TEXT,
    at_bats     INTEGER,
    hits        INTEGER,
    home_runs   INTEGER,
    rbi         INTEGER,
    walks       INTEGER,
    strikeouts  INTEGER,
    avg         DOUBLE PRECISION,
    PRIMARY KEY (player_id, season, game_date, game_index)
);

CREATE TABLE IF NOT EXISTS player_game_log_pitching (
    player_id        BIGINT NOT NULL,
    season           INTEGER NOT NULL,
    game_date        DATE NOT NULL,
    game_index       SMALLINT NOT NULL DEFAULT 0,
    opponent         TEXT,
    innings_pitched  DOUBLE PRECISION,
    hits             INTEGER,
    earned_runs      INTEGER,
    strikeouts       INTEGER,
    walks            INTEGER,
    era              DOUBLE PRECISION,
    PRIMARY KEY (player_id, season, game_date, game_index)
);

-- Team season stats: currently zero call sites in app.py (Team Trends is
-- commented out) -- cached anyway for when that's revived. Tiny volume
-- (30 teams x ~125 years x 2 groups), lazy-only for consistency with the
-- player-level tables above rather than a special-cased backfill.
CREATE TABLE IF NOT EXISTS team_season_hitting_stats (
    team_id      INTEGER NOT NULL,
    season       INTEGER NOT NULL,
    runs         INTEGER,
    avg          DOUBLE PRECISION,
    obp          DOUBLE PRECISION,
    slg          DOUBLE PRECISION,
    ops          DOUBLE PRECISION,
    games_played INTEGER,
    PRIMARY KEY (team_id, season)
);

CREATE TABLE IF NOT EXISTS team_season_pitching_stats (
    team_id      INTEGER NOT NULL,
    season       INTEGER NOT NULL,
    wins         INTEGER,
    losses       INTEGER,
    runs_allowed INTEGER,
    era          DOUBLE PRECISION,
    whip         DOUBLE PRECISION,
    games_played INTEGER,
    PRIMARY KEY (team_id, season)
);
