-- Postgres cache for the all-time roster / player-bio data behind the
-- dashboard's position checkboxes (see macroservice/roster_history_db.py).
--
-- Applied idempotently by roster_history_db.ensure_schema() on every
-- backfill run, so this file is the single source of truth for the schema
-- -- there is no separate migration tool. Future changes append
-- ALTER TABLE ... IF NOT EXISTS statements here rather than being managed
-- as versioned migrations; the scope (two tables, one writer, changes a
-- few times a year) doesn't justify Alembic.

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
