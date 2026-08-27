"""Season leaderboard queries for the Insights page: top N players in a
given metric, among a selectable set of teams, for one season.

Deliberately Streamlit-free (same convention as roster_history_db.py and
season_stats_db.py) -- callers supply an already-open SQLAlchemy Engine.

Unlike client.py's other caches, there is no live-API fallback here: a
leaderboard needs real coverage across many players to mean anything, and
falling back to the live API on a miss would mean thousands of API calls on
a single page load. Coverage instead comes from a dedicated backfill script
(scripts/backfill_season_leaderboard.py) that populates player_season_team
plus the existing season-stats/Statcast tables for a whole season at once.

Ranking direction is domain-correct, not literally "always highest": ERA,
WHIP, and walks allowed by a pitcher rank ascending (lowest is best) --
everything else, including strikeouts thrown by a pitcher (more is better),
ranks descending.
"""
from __future__ import annotations

from sqlalchemy import Engine, text

# metric key -> (table, column, ascending). ascending=True means "lowest
# value wins" (ERA, WHIP, walks allowed) -- everything else is descending
# ("highest value wins"), including a pitcher's own strikeouts (more Ks
# thrown is better, unlike walks allowed).
_HITTING_METRIC_REGISTRY: dict[str, tuple[str, str, bool]] = {
    "avg": ("player_season_hitting_stats", "avg", False),
    "obp": ("player_season_hitting_stats", "obp", False),
    "slg": ("player_season_hitting_stats", "slg", False),
    "ops": ("player_season_hitting_stats", "ops", False),
    "homeRuns": ("player_season_hitting_stats", "home_runs", False),
    "rbi": ("player_season_hitting_stats", "rbi", False),
    "strikeOuts": ("player_season_hitting_stats", "strikeouts", False),
    "baseOnBalls": ("player_season_hitting_stats", "walks", False),
    "xba": ("player_statcast_hitting_season", "xba", False),
    "avgExitVelocity": ("player_statcast_hitting_season", "avg_exit_velocity", False),
    "hardHitPct": ("player_statcast_hitting_season", "hard_hit_pct", False),
    "barrelPct": ("player_statcast_hitting_season", "barrel_pct", False),
}

_PITCHING_METRIC_REGISTRY: dict[str, tuple[str, str, bool]] = {
    "era": ("player_season_pitching_stats", "era", True),
    "whip": ("player_season_pitching_stats", "whip", True),
    "strikeOuts": ("player_season_pitching_stats", "strikeouts", False),
    "baseOnBalls": ("player_season_pitching_stats", "walks", True),
    "inningsPitched": ("player_season_pitching_stats", "innings_pitched", False),
    "earnedRuns": ("player_season_pitching_stats", "earned_runs", True),
    "cswPct": ("player_statcast_pitching_season", "csw_pct", False),
    "whiffPct": ("player_statcast_pitching_season", "whiff_pct", False),
    "chasePct": ("player_statcast_pitching_season", "chase_pct", False),
    "avgVelocity": ("player_statcast_pitching_season", "avg_velocity", False),
}


_UPSERT_PLAYER_SEASON_TEAM_SQL = text("""
    INSERT INTO player_season_team (player_id, team_id, season, position, is_pitcher)
    VALUES (:player_id, :team_id, :season, :position, :is_pitcher)
    ON CONFLICT (player_id, team_id, season) DO UPDATE SET
        position = EXCLUDED.position, is_pitcher = EXCLUDED.is_pitcher
""")


def upsert_player_season_team(engine: Engine, rows: list[dict]) -> None:
    """Writes season-scoped team-membership rows (see db/schema.sql's
    player_season_team) -- used by scripts/backfill_season_leaderboard.py.
    Each row: {player_id, team_id, season, position, is_pitcher}. Requires
    each player_id to already exist in ``players`` (FK) -- callers must
    upsert bios first (roster_history_db.upsert_players_bio).
    """
    if not rows:
        return
    with engine.begin() as conn:
        conn.execute(_UPSERT_PLAYER_SEASON_TEAM_SQL, rows)


def is_ascending_metric(metric_key: str, group: str) -> bool:
    """True when "lowest value wins" for this metric (e.g. ERA)."""
    registry = _PITCHING_METRIC_REGISTRY if group == "pitching" else _HITTING_METRIC_REGISTRY
    return registry[metric_key][2]


def top_players_by_metric(
    engine: Engine, metric_key: str, group: str, season: int, team_ids: frozenset[int], limit: int = 10
) -> list[dict]:
    """Top ``limit`` players for one metric/season among ``team_ids``.

    Each result dict has player_id/name/debut_year/last_active_year/active/
    metric_value. A plain SELECT DISTINCT (not DISTINCT ON + a subquery) is
    enough to dedupe: player_season_*_stats are keyed (player_id, season),
    not (player_id, team_id, season), so a player traded between two
    currently-selected teams produces duplicate IDENTICAL rows via the
    join fan-out (same metric value both times), never duplicate values.

    ``table``/``column`` are interpolated from the fixed registries above
    (never from caller-supplied input), so this isn't a SQL-injection
    surface despite the f-string.
    """
    registry = _PITCHING_METRIC_REGISTRY if group == "pitching" else _HITTING_METRIC_REGISTRY
    table, column, ascending = registry[metric_key]
    order = "ASC" if ascending else "DESC"
    sql = text(f"""
        SELECT DISTINCT p.id AS player_id, p.name, p.debut_year, p.last_active_year, p.active,
               m.{column} AS metric_value
        FROM {table} m
        JOIN player_season_team pst ON pst.player_id = m.player_id AND pst.season = m.season
        JOIN players p ON p.id = m.player_id
        WHERE m.season = :season AND pst.team_id = ANY(:team_ids) AND m.{column} IS NOT NULL
        ORDER BY m.{column} {order}
        LIMIT :limit
    """)
    with engine.connect() as conn:
        rows = conn.execute(sql, {"season": season, "team_ids": list(team_ids), "limit": limit}).mappings().all()
    return [dict(row) for row in rows]
