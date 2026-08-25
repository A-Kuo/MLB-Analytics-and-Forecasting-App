"""Season-level aggregates from Baseball Savant's pitch-by-pitch and
batted-ball data (2015+ only -- Statcast doesn't exist before then). The
season-level counterpart to macroservice/features.py's per-game rolling
feature engineering: these functions collapse a whole season's raw rows
into one number per metric, for the dashboard's Aggregate KPI/Performance
Trend/Forecast paths. macroservice/players.py's plain MLB Stats API
equivalents cover 1901-present; these cover 2015-present only, and are
meant to be selected alongside them, not replace them.

Formulas confirmed against real data (Corbin Carroll 2024, Brandon Pfaadt
2024): barrel% uses Statcast's own launch_speed_angle==6 classification --
the raw CSV already carries the official call, no re-derived threshold
needed. CSW%/whiff%/chase%/velocity all landed within a point or two of
real 2024 league averages during validation. xBA here is the mean of each
batted ball's own estimated_ba_using_speedangle -- an approximation of
Baseball Savant's official season xBA, which also factors in strikeouts.
"""
from __future__ import annotations

from macroservice import statcast
from macroservice.caching import cached
from macroservice.features import CSW_DESCRIPTIONS, HARD_HIT_LAUNCH_SPEED_MPH, SWING_DESCRIPTIONS, WHIFF_DESCRIPTIONS

STATCAST_ERA_START_YEAR = 2015
BARREL_LAUNCH_SPEED_ANGLE_CODE = "6"
OUT_OF_ZONE_CODES = {"11", "12", "13", "14"}
SEASON_AGGREGATE_TTL_SECONDS = 60 * 60

_EMPTY_HITTER_SEASON = {"xba": None, "avgExitVelocity": None, "hardHitPct": None, "barrelPct": None}
_EMPTY_PITCHER_SEASON = {"cswPct": None, "whiffPct": None, "chasePct": None, "avgVelocity": None}


def _to_float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


@cached(ttl_seconds=SEASON_AGGREGATE_TTL_SECONDS)
def compute_hitter_statcast_season(player_id: int, season: int) -> dict:
    """{"xba", "avgExitVelocity", "hardHitPct", "barrelPct"} for one season
    -- every value None when season < 2015 or there's no batted-ball data
    for this player/season (never raises; a graceful "unavailable" case,
    matching how the rest of this codebase treats missing Statcast data).
    """
    if season < STATCAST_ERA_START_YEAR:
        return dict(_EMPTY_HITTER_SEASON)

    rows = statcast.get_batter_batted_balls(player_id, season)
    if not rows:
        return dict(_EMPTY_HITTER_SEASON)

    exit_velos = [v for v in (_to_float(r.get("launch_speed")) for r in rows) if v is not None]
    xbas = [v for v in (_to_float(r.get("estimated_ba_using_speedangle")) for r in rows) if v is not None]
    barrels = sum(1 for r in rows if r.get("launch_speed_angle") == BARREL_LAUNCH_SPEED_ANGLE_CODE)

    return {
        "xba": _mean(xbas),
        "avgExitVelocity": _mean(exit_velos),
        "hardHitPct": (sum(1 for v in exit_velos if v >= HARD_HIT_LAUNCH_SPEED_MPH) / len(exit_velos))
        if exit_velos
        else None,
        "barrelPct": barrels / len(rows),
    }


@cached(ttl_seconds=SEASON_AGGREGATE_TTL_SECONDS)
def compute_pitcher_statcast_season(player_id: int, season: int) -> dict:
    """{"cswPct", "whiffPct", "chasePct", "avgVelocity"} for one season --
    every value None when season < 2015 or there's no pitch data for this
    player/season.
    """
    if season < STATCAST_ERA_START_YEAR:
        return dict(_EMPTY_PITCHER_SEASON)

    rows = statcast.get_pitcher_pitches(player_id, season)
    if not rows:
        return dict(_EMPTY_PITCHER_SEASON)

    total = len(rows)
    csw = sum(1 for r in rows if r.get("description") in CSW_DESCRIPTIONS)
    swings = sum(1 for r in rows if r.get("description") in SWING_DESCRIPTIONS)
    whiffs = sum(1 for r in rows if r.get("description") in WHIFF_DESCRIPTIONS)
    out_of_zone = [r for r in rows if r.get("zone") in OUT_OF_ZONE_CODES]
    out_of_zone_swings = sum(1 for r in out_of_zone if r.get("description") in SWING_DESCRIPTIONS)
    velocities = [v for v in (_to_float(r.get("release_speed")) for r in rows) if v is not None]

    return {
        "cswPct": csw / total,
        "whiffPct": (whiffs / swings) if swings else None,
        "chasePct": (out_of_zone_swings / len(out_of_zone)) if out_of_zone else None,
        "avgVelocity": _mean(velocities),
    }


def get_hitter_statcast_series(player_id: int, metric: str, start_year: int, end_year: int) -> dict:
    """Same {"years": [...], "values": [...]} shape as
    players.get_season_series -- the Statcast analogue, skipping years
    before the Statcast era and years with no data for this player.
    """
    years: list[int] = []
    values: list[float] = []
    for year in range(max(start_year, STATCAST_ERA_START_YEAR), end_year + 1):
        value = compute_hitter_statcast_season(player_id, year).get(metric)
        if value is None:
            continue
        years.append(year)
        values.append(value)
    return {"years": years, "values": values}


def get_pitcher_statcast_series(player_id: int, metric: str, start_year: int, end_year: int) -> dict:
    years: list[int] = []
    values: list[float] = []
    for year in range(max(start_year, STATCAST_ERA_START_YEAR), end_year + 1):
        value = compute_pitcher_statcast_season(player_id, year).get(metric)
        if value is None:
            continue
        years.append(year)
        values.append(value)
    return {"years": years, "values": values}
