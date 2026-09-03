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
