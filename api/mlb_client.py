"""Thin wrapper around the public MLB Stats API (statsapi.mlb.com).

No authentication is required for read access. Roster data changes rarely
within a season so it is cached longer than game logs, which are polled
near-real-time so newly posted games show up quickly.
"""
from __future__ import annotations

import pandas as pd
import requests

from api.cache_manager import cached

BASE_URL = "https://statsapi.mlb.com/api/v1"
REQUEST_TIMEOUT = 10

ROSTER_TTL_SECONDS = 60 * 60  # rosters rarely change intra-day
GAME_LOG_TTL_SECONDS = 60  # matches the README's default live-poll interval
PLAYER_INFO_TTL_SECONDS = 60 * 60 * 24


@cached(ttl_seconds=ROSTER_TTL_SECONDS)
def get_roster(team_id: int, season: int) -> list[dict]:
    """Active roster for a team/season as [{id, name, position, is_pitcher}]."""
    resp = requests.get(
        f"{BASE_URL}/teams/{team_id}/roster",
        params={"season": season},
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    roster = resp.json().get("roster", [])
    return [
        {
            "id": entry["person"]["id"],
            "name": entry["person"]["fullName"],
            "position": entry["position"]["abbreviation"],
            "is_pitcher": entry["position"]["abbreviation"] == "P",
        }
        for entry in roster
    ]


@cached(ttl_seconds=PLAYER_INFO_TTL_SECONDS)
def get_player_info(player_id: int) -> dict:
    """Bio info for a player (headshot-ready id, bats/throws, etc.)."""
    resp = requests.get(f"{BASE_URL}/people/{player_id}", timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    people = resp.json().get("people", [])
    return people[0] if people else {}


@cached(ttl_seconds=GAME_LOG_TTL_SECONDS)
def get_player_game_log(player_id: int, season: int, group: str = "hitting") -> list[dict]:
    """Raw per-game splits for a player, as returned by the stats endpoint."""
    resp = requests.get(
        f"{BASE_URL}/people/{player_id}/stats",
        params={"stats": "gameLog", "group": group, "season": season},
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    stats = resp.json().get("stats", [])
    return stats[0].get("splits", []) if stats else []


@cached(ttl_seconds=GAME_LOG_TTL_SECONDS)
def get_player_season_stats(player_id: int, season: int, group: str = "hitting") -> dict:
    """Cumulative season stat line for a player, e.g. {"avg": ".287", ...}."""
    resp = requests.get(
        f"{BASE_URL}/people/{player_id}/stats",
        params={"stats": "season", "group": group, "season": season},
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    stats = resp.json().get("stats", [])
    splits = stats[0].get("splits", []) if stats else []
    return splits[0]["stat"] if splits else {}


@cached(ttl_seconds=GAME_LOG_TTL_SECONDS)
def get_team_schedule(team_id: int, season: int) -> list[dict]:
    """Raw schedule entries (with linescores) for a team/season."""
    resp = requests.get(
        f"{BASE_URL}/schedule",
        params={
            "hydrate": "linescore,team",
            "teamId": team_id,
            "season": season,
            "sportId": 1,
            "gameType": "R",
        },
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    dates = resp.json().get("dates", [])
    return [game for date in dates for game in date.get("games", [])]


def team_schedule_dataframe(team_id: int, season: int) -> pd.DataFrame:
    """Completed games for a team/season with 1st/2nd-half inning splits.

    Mirrors the EDA notebook's schedule feature set: ``team_first_half`` /
    ``team_second_half`` / ``team_total_runs`` (innings 1-4 / 5+ / both) and
    the same three fields for the opponent, plus ``win`` and ``is_home``.
    """
    rows = []
    for game in get_team_schedule(team_id, season):
        if game.get("status", {}).get("abstractGameState") != "Final":
            continue
        innings = (game.get("linescore") or {}).get("innings") or []
        if not innings:
            continue

        teams = game.get("teams", {})
        is_home = teams.get("home", {}).get("team", {}).get("id") == team_id
        side, opp_side = ("home", "away") if is_home else ("away", "home")

        team_first = sum((i.get(side) or {}).get("runs") or 0 for i in innings if (i.get("num") or 0) <= 4)
        team_second = sum((i.get(side) or {}).get("runs") or 0 for i in innings if (i.get("num") or 0) > 4)
        opp_first = sum((i.get(opp_side) or {}).get("runs") or 0 for i in innings if (i.get("num") or 0) <= 4)
        opp_second = sum((i.get(opp_side) or {}).get("runs") or 0 for i in innings if (i.get("num") or 0) > 4)

        rows.append(
            {
                "date": game.get("officialDate"),
                "opponent": teams.get(opp_side, {}).get("team", {}).get("name", ""),
                "is_home": is_home,
                "team_first_half": team_first,
                "team_second_half": team_second,
                "team_total_runs": team_first + team_second,
                "opp_first_half": opp_first,
                "opp_second_half": opp_second,
                "opp_total_runs": opp_first + opp_second,
                "win": int((team_first + team_second) > (opp_first + opp_second)),
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)


def game_log_dataframe(player_id: int, season: int, group: str = "hitting") -> pd.DataFrame:
    """Per-game log as a DataFrame, sorted chronologically.

    One row per game with the opponent name and that game's stat line
    flattened into columns (e.g. ``avg``, ``homeRuns``, ``era``) — the shape
    both the trend chart and the game log table are built from.
    """
    splits = get_player_game_log(player_id, season, group)
    rows = []
    for split in splits:
        row = {
            "date": split.get("date"),
            "opponent": split.get("opponent", {}).get("name", ""),
            "is_home": split.get("isHome", False),
        }
        row.update(split.get("stat", {}))
        rows.append(row)

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    for col in ("avg", "obp", "slg", "ops", "era", "whip"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df
