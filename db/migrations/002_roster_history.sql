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
