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
    # Statcast-derived (macroservice/statcast_season.py), 2015+ only --
    # folded into the same list rather than a separate section so every
    # checkbox panel/aggregation path handles them uniformly; the "(Statcast,
    # 2015+)" suffix on the full name (below) is what self-documents the
    # coverage gap, not a UI grouping.
    ("xba", "xBA"),
    ("avgExitVelocity", "EV"),
    ("hardHitPct", "Hard-Hit%"),
    ("barrelPct", "Barrel%"),
]

PITCHING_METRICS: list[tuple[str, str]] = [
    ("era", "ERA"),
    ("whip", "WHIP"),
    ("strikeOuts", "K"),
    ("baseOnBalls", "BB"),
    ("inningsPitched", "IP"),
    ("earnedRuns", "ER"),
    # Statcast-derived, 2015+ only -- see note above.
    ("cswPct", "CSW%"),
    ("whiffPct", "Whiff%"),
    ("chasePct", "Chase%"),
    ("avgVelocity", "Velo"),
]

# Metric keys backed by macroservice/statcast_season.py rather than the
# plain MLB Stats API season-stats endpoint -- lets client.py's dispatcher
# route each metric to the right backend without every call site needing
# to know which one a given key came from.
STATCAST_METRIC_KEYS: frozenset[str] = frozenset(
    {"xba", "avgExitVelocity", "hardHitPct", "barrelPct", "cswPct", "whiffPct", "chasePct", "avgVelocity"}
)

# Statcast percentages/rates sit on the same small 0-1-ish scale as the
# plain-API rate stats (avg/obp/.../era/whip) -- but avgExitVelocity/
# avgVelocity are ~85-105 mph, an entirely different scale that's actually
# closer to the counting stats (HR, RBI, ...) than to a 0-1 rate. Excluding
# them here keeps them off the rate axis so they don't flatten into the
# baseline next to a .300 batting average.
_STATCAST_RATE_METRICS: frozenset[str] = STATCAST_METRIC_KEYS - {"avgExitVelocity", "avgVelocity"}

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
    "xba": "Expected Batting Average (xBA, Statcast 2015+)",
    "avgExitVelocity": "Average Exit Velocity (Statcast 2015+)",
    "hardHitPct": "Hard-Hit% (Statcast 2015+)",
    "barrelPct": "Barrel% (Statcast 2015+)",
    "cswPct": "Called Strike + Whiff % (CSW%, Statcast 2015+)",
    "whiffPct": "Whiff% (Statcast 2015+)",
    "chasePct": "Chase% (Statcast 2015+)",
    "avgVelocity": "Average Velocity (Statcast 2015+)",
}

# Rate stats sit on a 0-ish to low-single-digit scale; counting stats run to
# the hundreds. Plotting both against one y-axis flattens the rate lines into
# the baseline, so the trend chart splits them across two axes. This is a
# CHART-AXIS set, not an aggregation-math set -- see MEAN_AGGREGATE_METRICS
# below for the (different) set that decides sum-vs-mean.
RATE_METRICS: frozenset[str] = frozenset(
    {"avg", "obp", "slg", "ops", "era", "whip"} | _STATCAST_RATE_METRICS
)

# Metrics that should be MEAN-combined across (player, year) points when
# aggregating a multi-player/multi-year selection (utils.aggregation),
# rather than summed. This is RATE_METRICS plus avgExitVelocity/avgVelocity:
# those two are deliberately excluded from RATE_METRICS (they'd flatten
# against a 0-1 rate axis on the trend chart -- see that set's comment),
# but they're still per-player averages, not counts, so summing them across
# a multi-season selection produces a meaningless total (e.g. "858 mph" for
# one player's decade of seasons, previously a live bug -- confirmed via
# direct reproduction against the Neon-backed aggregate-KPI path).
MEAN_AGGREGATE_METRICS: frozenset[str] = RATE_METRICS | {"avgExitVelocity", "avgVelocity"}


def stat_group_for_position(position_abbr: str) -> str:
    """"P" rostered players are pitchers (defense); everyone else is offense."""
    return "pitching" if position_abbr == "P" else "hitting"


def metrics_for_group(group: str) -> list[tuple[str, str]]:
    return PITCHING_METRICS if group == "pitching" else HITTING_METRICS


def full_name_for_metric(key: str) -> str:
    return METRIC_FULL_NAMES.get(key, key)


def is_rate_metric(key: str) -> bool:
    return key in RATE_METRICS


def is_mean_aggregated(key: str) -> bool:
    return key in MEAN_AGGREGATE_METRICS
