"""Offense/defense stat-group logic for an individually selected player.

Given the roster position of the selected player, decide whether they're
viewed as a hitter or a pitcher and which metric keys apply.
"""
from __future__ import annotations

# (MLB Stats API field, acronym) -- the acronym is what chart legends and
# KPI cards show. Full names (for the metric checkbox panel) are below.
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


# Spelled-out metric names for the trend chart's checkbox panel; the chart
# legend stays on the acronyms above so it doesn't crowd the plot area.
METRIC_FULL_NAMES: dict[str, str] = {
    "avg": "Batting Average",
    "obp": "On-Base Percentage",
    "slg": "Slugging Percentage",
    "ops": "On-Base Plus Slugging",
    "homeRuns": "Home Runs",
    "rbi": "Runs Batted In",
    "strikeOuts": "Strikeouts",
    "baseOnBalls": "Walks",
    "era": "Earned Run Average",
    "whip": "Walks + Hits per Inning Pitched",
    "inningsPitched": "Innings Pitched",
    "earnedRuns": "Earned Runs",
}

# Rate stats sit on a 0-ish to low-single-digit scale; counting stats run to
# the hundreds. Plotting both against one y-axis flattens the rate lines into
# the baseline, so the trend chart splits them across two axes.
RATE_METRICS: frozenset[str] = frozenset({"avg", "obp", "slg", "ops", "era", "whip"})


def stat_group_for_position(position_abbr: str) -> str:
    """"P" rostered players are pitchers (defense); everyone else is offense."""
    return "pitching" if position_abbr == "P" else "hitting"


def metrics_for_group(group: str) -> list[tuple[str, str]]:
    return PITCHING_METRICS if group == "pitching" else HITTING_METRICS


def full_name_for_metric(key: str) -> str:
    return METRIC_FULL_NAMES.get(key, key)


def is_rate_metric(key: str) -> bool:
    return key in RATE_METRICS
