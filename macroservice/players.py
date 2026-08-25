"""Player game log and season stats -- MLB Stats API player-scoped resources."""
from __future__ import annotations

from macroservice.backoff import request_with_backoff
from macroservice.caching import cached

BASE_URL = "https://statsapi.mlb.com/api/v1"
GAME_DATA_TTL_SECONDS = 60  # near-real-time: picks up newly posted games quickly
HEADSHOT_URL_TEMPLATE = (
    "https://img.mlbstatic.com/mlb-photos/image/upload/"
    "d_people:generic:headshot:67:current.png/w_{width},q_auto:best/"
    "v1/people/{player_id}/headshot/67/current"
)


def headshot_url(player_id: int, width: int = 213) -> str:
    """MLB's headshot CDN. The ``d_people:generic:...`` fallback segment means
    an unknown/photo-less player_id resolves to a generic silhouette instead
    of a broken image, so callers never need to handle a missing photo.
    """
    return HEADSHOT_URL_TEMPLATE.format(width=width, player_id=player_id)


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
