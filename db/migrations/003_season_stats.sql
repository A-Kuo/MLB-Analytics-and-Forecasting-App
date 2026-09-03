-- Season stats and game logs (see macroservice/season_stats_db.py). Lazy,
-- self-healing caches -- populated as the dashboard is actually used, not
-- backfilled -- and only ever written for a season once it's confirmed
-- complete (client.py's freshness split): the current in-progress season
-- always bypasses these tables and hits the live API directly, since these
-- stats change every game. Column sets match exactly what utils/filters.py's
-- HITTING_METRICS/PITCHING_METRICS (plain-API subset) and GAME_LOG_COLUMNS
-- already define -- the fields this app actually reads, not the full raw
-- API response.

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

-- game_index disambiguates true doubleheaders (two games, same date) --
-- a fallback tiebreaker, not a verified real game id; see
-- macroservice/season_stats_db.py's _dedupe_game_index for where this
-- gets computed.
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
