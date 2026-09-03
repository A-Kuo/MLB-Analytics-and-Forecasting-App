CREATE INDEX IF NOT EXISTS idx_roster_stints_team_id
    ON roster_stints (team_id);

CREATE INDEX IF NOT EXISTS idx_player_season_team_season_team
    ON player_season_team (season, team_id);

CREATE INDEX IF NOT EXISTS idx_player_season_hitting_season
    ON player_season_hitting_stats (season);

CREATE INDEX IF NOT EXISTS idx_player_season_pitching_season
    ON player_season_pitching_stats (season);

CREATE INDEX IF NOT EXISTS idx_statcast_hitting_season
    ON player_statcast_hitting_season (season);

CREATE INDEX IF NOT EXISTS idx_statcast_pitching_season
    ON player_statcast_pitching_season (season);

CREATE INDEX IF NOT EXISTS idx_team_news_team_published
    ON team_news (team_id, published_at DESC);
