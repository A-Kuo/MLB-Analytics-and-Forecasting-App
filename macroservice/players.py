"""Player game log and season stats -- MLB Stats API player-scoped resources."""
from __future__ import annotations

from macroservice.backoff import request_with_backoff
from macroservice.caching import cached

BASE_URL = "https://statsapi.mlb.com/api/v1"
GAME_DATA_TTL_SECONDS = 60  # near-real-time: picks up newly posted games quickly


@cached(ttl_seconds=GAME_DATA_TTL_SECONDS)
def get_game_log(player_id: int, season: int, group: str = "hitting") -> list[dict]:
    resp = request_with_backoff(
        "GET",
        f"{BASE_URL}/people/{player_id}/stats",
        params={"stats": "gameLog", "group": group, "season": season},
    )
    resp.raise_for_status()
    stats = resp.json().get("stats", [])
    return stats[0].get("splits", []) if stats else []


@cached(ttl_seconds=GAME_DATA_TTL_SECONDS)
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
