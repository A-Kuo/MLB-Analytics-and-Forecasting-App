"""Offense/defense stat-group logic for an individually selected player.

v1 scope is intentionally player-only: given the roster position of the
selected player, decide whether they're viewed as a hitter or a pitcher and
which metric keys apply. Team-aggregate offense/defense splitting is v1.1
(see README roadmap).
"""
from __future__ import annotations

# (MLB Stats API field, display label) for the trend-chart metric dropdown.
HITTING_METRICS: list[tuple[str, str]] = [
    ("avg", "AVG"),
    ("obp", "OBP"),
    ("slg", "SLG"),
    ("ops", "OPS"),
    ("homeRuns", "HR"),
    ("rbi", "RBI"),
    ("strikeOuts", "K"),
    ("baseOnBalls", "BB"),
]

PITCHING_METRICS: list[tuple[str, str]] = [
    ("era", "ERA"),
    ("whip", "WHIP"),
    ("strikeOuts", "K"),
    ("baseOnBalls", "BB"),
    ("inningsPitched", "IP"),
    ("earnedRuns", "ER"),
]

# Columns pulled from the per-game log for the expandable game-log table.
GAME_LOG_COLUMNS: dict[str, list[str]] = {
    "hitting": ["date", "opponent", "atBats", "hits", "homeRuns", "rbi", "baseOnBalls", "strikeOuts", "avg"],
    "pitching": ["date", "opponent", "inningsPitched", "hits", "earnedRuns", "strikeOuts", "baseOnBalls", "era"],
}


def stat_group_for_position(position_abbr: str) -> str:
    """"P" rostered players are pitchers (defense); everyone else is offense."""
    return "pitching" if position_abbr == "P" else "hitting"


def metrics_for_group(group: str) -> list[tuple[str, str]]:
    return PITCHING_METRICS if group == "pitching" else HITTING_METRICS
