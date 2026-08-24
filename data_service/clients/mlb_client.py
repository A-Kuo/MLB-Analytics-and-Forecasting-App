"""MLB Stats API client: rosters, player game logs, season stats, team schedule."""
from __future__ import annotations

from backoff import request_with_backoff

BASE_URL = "https://statsapi.mlb.com/api/v1"


def get_roster(team_id: int, season: int) -> list[dict]:
    resp = request_with_backoff("GET", f"{BASE_URL}/teams/{team_id}/roster", params={"season": season})
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


def get_game_log(player_id: int, season: int, group: str = "hitting") -> list[dict]:
    resp = request_with_backoff(
        "GET",
        f"{BASE_URL}/people/{player_id}/stats",
        params={"stats": "gameLog", "group": group, "season": season},
    )
    resp.raise_for_status()
    stats = resp.json().get("stats", [])
    return stats[0].get("splits", []) if stats else []


def get_season_stats(player_id: int, season: int, group: str = "hitting") -> dict:
    resp = request_with_backoff(
        "GET",
        f"{BASE_URL}/people/{player_id}/stats",
        params={"stats": "season", "group": group, "season": season},
    )
    resp.raise_for_status()
    stats = resp.json().get("stats", [])
    splits = stats[0].get("splits", []) if stats else []
    return splits[0]["stat"] if splits else {}


def get_schedule(team_id: int, season: int) -> list[dict]:
    resp = request_with_backoff(
        "GET",
        f"{BASE_URL}/schedule",
        params={
            "hydrate": "linescore,team",
            "teamId": team_id,
            "season": season,
            "sportId": 1,
            "gameType": "R",
        },
    )
    resp.raise_for_status()
    dates = resp.json().get("dates", [])
    return [game for date in dates for game in date.get("games", [])]
