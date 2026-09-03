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

from macroservice.sql import load_query

# metric key -> (view, column, ascending). ascending=True means "lowest
# value wins" (ERA, WHIP, walks allowed) -- everything else is descending
# ("highest value wins"), including a pitcher's own strikeouts (more Ks
# thrown is better, unlike walks allowed). view is v_insights_hitting/
# v_insights_pitching (db/views/) -- both already join player_season_team +
# the season-stats/Statcast tables + players, so a lookup here needs no
# JOIN of its own, just a column/sort choice.
_HITTING_METRIC_REGISTRY: dict[str, tuple[str, str, bool]] = {
    "avg": ("v_insights_hitting", "avg", False),
    "obp": ("v_insights_hitting", "obp", False),
    "slg": ("v_insights_hitting", "slg", False),
    "ops": ("v_insights_hitting", "ops", False),
    "homeRuns": ("v_insights_hitting", "home_runs", False),
    "rbi": ("v_insights_hitting", "rbi", False),
    "strikeOuts": ("v_insights_hitting", "strikeouts", False),
    "baseOnBalls": ("v_insights_hitting", "walks", False),
    "xba": ("v_insights_hitting", "xba", False),
    "avgExitVelocity": ("v_insights_hitting", "avg_exit_velocity", False),
    "hardHitPct": ("v_insights_hitting", "hard_hit_pct", False),
    "barrelPct": ("v_insights_hitting", "barrel_pct", False),
}

_PITCHING_METRIC_REGISTRY: dict[str, tuple[str, str, bool]] = {
    "era": ("v_insights_pitching", "era", True),
    "whip": ("v_insights_pitching", "whip", True),
    "strikeOuts": ("v_insights_pitching", "strikeouts", False),
    "baseOnBalls": ("v_insights_pitching", "walks", True),
    "inningsPitched": ("v_insights_pitching", "innings_pitched", False),
    "earnedRuns": ("v_insights_pitching", "earned_runs", True),
    "cswPct": ("v_insights_pitching", "csw_pct", False),
    "whiffPct": ("v_insights_pitching", "whiff_pct", False),
    "chasePct": ("v_insights_pitching", "chase_pct", False),
    "avgVelocity": ("v_insights_pitching", "avg_velocity", False),
}

_LEADERBOARD_SQL_TEMPLATE = load_query("insights", "leaderboard.sql")
_UPSERT_PLAYER_SEASON_TEAM_SQL = text(load_query("insights", "upsert_player_season_team.sql"))


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
    metric_value. See db/queries/insights/leaderboard.sql for the dedupe
    rationale (a plain SELECT DISTINCT, not DISTINCT ON + a subquery).

    ``view``/``column`` are interpolated from the fixed registries above
    (never from caller-supplied input), so this isn't a SQL-injection
    surface despite the runtime template substitution.
    """
    registry = _PITCHING_METRIC_REGISTRY if group == "pitching" else _HITTING_METRIC_REGISTRY
    view, column, ascending = registry[metric_key]
    order = "ASC" if ascending else "DESC"
    sql = text(_LEADERBOARD_SQL_TEMPLATE.format(view=view, column=column, order=order))
    with engine.connect() as conn:
        rows = conn.execute(sql, {"season": season, "team_ids": list(team_ids), "limit": limit}).mappings().all()
    return [dict(row) for row in rows]
