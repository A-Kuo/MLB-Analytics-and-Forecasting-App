"""Baseball Savant (Statcast) pitch-level data.

Backs the defensive CSW% trajectory engine (pitch-by-pitch) and the batted-ball
features (exit velocity, xBA, hard-hit%) that feed the offensive trajectory
engine. Unlike statsapi.mlb.com, Baseball Savant has no documented/stable
public API -- this hits its CSV export endpoint directly. Every caller must
treat an empty DataFrame as a legitimate "no Statcast data" outcome (network
failure, rate limit, or a player with no recorded pitches/batted balls) and
fall back to MLB Stats API-derived metrics rather than erroring out.
"""
from __future__ import annotations

import io

import pandas as pd
import requests

from api.cache_manager import cached

SEARCH_URL = "https://baseballsavant.mlb.com/statcast_search/csv"
REQUEST_TIMEOUT = 30
STATCAST_TTL_SECONDS = 60 * 60  # 1 hour, per the Statcast ingestion-caching guideline

_COMMON_PARAMS = {"all": "true", "hfGT": "R|", "type": "details"}


@cached(ttl_seconds=STATCAST_TTL_SECONDS)
def _fetch_statcast(player_type: str, player_id: int, season: int) -> pd.DataFrame:
    lookup_key = "pitchers_lookup[]" if player_type == "pitcher" else "batters_lookup[]"
    params = {
        **_COMMON_PARAMS,
        "hfSea": f"{season}|",
        "player_type": player_type,
        "game_date_gt": f"{season}-01-01",
        "game_date_lt": f"{season}-12-31",
        lookup_key: player_id,
    }
    try:
        resp = requests.get(SEARCH_URL, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException:
        return pd.DataFrame()

    if not resp.text.strip():
        return pd.DataFrame()
    try:
        return pd.read_csv(io.StringIO(resp.text))
    except (pd.errors.ParserError, pd.errors.EmptyDataError):
        return pd.DataFrame()


def get_pitcher_pitches(player_id: int, season: int) -> pd.DataFrame:
    """Every pitch thrown by this pitcher in ``season``, or empty if unavailable."""
    return _fetch_statcast("pitcher", player_id, season)


def get_batter_batted_balls(player_id: int, season: int) -> pd.DataFrame:
    """Every batted-ball event (balls in play) for this hitter in ``season``."""
    df = _fetch_statcast("batter", player_id, season)
    if df.empty or "type" not in df.columns:
        return df
    return df[df["type"] == "X"].copy()  # type == "X" is Statcast's "ball in play" code
