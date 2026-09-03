-- Who was actually on team X during season Y specifically
-- (macroservice.teams.get_roster(team_id, season)) -- distinct from
-- roster_stints, which is all-time with no season scoping and would
-- incorrectly include a player long-traded away by season Y. Powers the
-- Insights leaderboard's team+season filter. team_id is part of the PK
-- (not just player_id, season) so a player traded mid-season legitimately
-- gets two rows for that season -- not a conflict, both real.
CREATE TABLE IF NOT EXISTS player_season_team (
    player_id  BIGINT NOT NULL REFERENCES players(id),
    team_id    INTEGER NOT NULL,
    season     INTEGER NOT NULL,
    position   TEXT,             -- roster-listed position abbreviation, informational only
    is_pitcher BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (player_id, team_id, season)
);
