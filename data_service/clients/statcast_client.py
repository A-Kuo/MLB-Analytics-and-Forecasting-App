"""Baseball Savant (Statcast) client: pitch-level pitcher data, batted-ball events.

Baseball Savant has no documented, stable public API -- this hits its CSV
search endpoint directly, parsed with the standard library's ``csv`` module
so this service carries no pandas/numpy dependency.
"""
from __future__ import annotations

import csv
import io

from backoff import request_with_backoff

SEARCH_URL = "https://baseballsavant.mlb.com/statcast_search/csv"
STATCAST_TIMEOUT_SECONDS = 30.0
_COMMON_PARAMS = {"all": "true", "hfGT": "R|", "type": "details"}


def _fetch(player_type: str, player_id: int, season: int) -> list[dict]:
    lookup_key = "pitchers_lookup[]" if player_type == "pitcher" else "batters_lookup[]"
    params = {
        **_COMMON_PARAMS,
        "hfSea": f"{season}|",
        "player_type": player_type,
        "game_date_gt": f"{season}-01-01",
        "game_date_lt": f"{season}-12-31",
        lookup_key: player_id,
    }
    resp = request_with_backoff("GET", SEARCH_URL, params=params, timeout=STATCAST_TIMEOUT_SECONDS)
    resp.raise_for_status()
    # utf-8-sig strips Baseball Savant's leading BOM; it would otherwise get
    # fused onto the first column's header (e.g. "pitch_type" -> a key with
    # a stray BOM character that no caller could match).
    text = resp.content.decode("utf-8-sig")
    if not text.strip():
        return []
    return list(csv.DictReader(io.StringIO(text)))


def get_pitcher_pitches(player_id: int, season: int) -> list[dict]:
    """Every pitch thrown by this pitcher in ``season``."""
    return _fetch("pitcher", player_id, season)


def get_batter_batted_balls(player_id: int, season: int) -> list[dict]:
    """Every batted-ball event (ball in play) for this hitter in ``season``."""
    rows = _fetch("batter", player_id, season)
    return [row for row in rows if row.get("type") == "X"]
