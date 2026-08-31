BEGIN;

CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS players (
    id BIGINT PRIMARY KEY,
    name TEXT NOT NULL,
    debut_year INTEGER,
    last_active_year INTEGER,
    active BOOLEAN NOT NULL DEFAULT FALSE
);

COMMIT;