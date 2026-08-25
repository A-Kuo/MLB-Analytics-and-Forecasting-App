"""Team config lookup, roster, and schedule -- MLB Stats API team-scoped resources."""
from __future__ import annotations

import json
from pathlib import Path

from macroservice.backoff import request_with_backoff
from macroservice.caching import cached

BASE_URL = "https://statsapi.mlb.com/api/v1"
ROSTER_TTL_SECONDS = 60 * 60
GAME_DATA_TTL_SECONDS = 60  # near-real-time: picks up newly posted games quickly

TEAMS_PATH = Path(__file__).parent / "config" / "teams.json"
TEAMS: list[dict] = json.loads(TEAMS_PATH.read_text())
TEAM_BY_ID: dict[int, dict] = {team["id"]: team for team in TEAMS}


class UnknownTeamError(ValueError):
    """Raised when a team_id isn't one of the known MLB teams."""


def require_known_team(team_id: int) -> None:
    if team_id not in TEAM_BY_ID:
        raise UnknownTeamError(f"Unknown team_id {team_id}")


@cached(ttl_seconds=ROSTER_TTL_SECONDS)
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


@cached(ttl_seconds=GAME_DATA_TTL_SECONDS)
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
