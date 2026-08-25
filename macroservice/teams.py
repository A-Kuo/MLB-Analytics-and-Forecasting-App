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


GENERAL_NEWS_HUB_URL = "https://www.mlb.com/news"

# Each team's dedicated news hub on mlb.com, verified live (session's Phase
# 0 research spike): 29 of 30 resolve from the plain lowercased nickname
# with spaces removed; Arizona is the sole irregular one ("dbacks", not
# "diamondbacks"). Hardcoded rather than derived from `nickname` at runtime
# so a future team whose nickname doesn't map cleanly fails safe (falls
# back to the general hub below) instead of silently linking to a 404.
TEAM_NEWS_HUB_SLUGS: dict[int, str] = {
    108: "angels",
    109: "dbacks",
    110: "orioles",
    111: "redsox",
    112: "cubs",
    113: "reds",
    114: "guardians",
    115: "rockies",
    116: "tigers",
    117: "astros",
    118: "royals",
    119: "dodgers",
    120: "nationals",
    121: "mets",
    133: "athletics",
    134: "pirates",
    135: "padres",
    136: "mariners",
    137: "giants",
    138: "cardinals",
    139: "rays",
    140: "rangers",
    141: "bluejays",
    142: "twins",
    143: "phillies",
    144: "braves",
    145: "whitesox",
    146: "marlins",
    147: "yankees",
    158: "brewers",
}


def team_news_hub_url(team_id: int) -> str:
    """The team's dedicated news hub, falling back to the general MLB.com
    hub for any id not in TEAM_NEWS_HUB_SLUGS (defensive -- every team
    known today has a verified slug, see above).
    """
    slug = TEAM_NEWS_HUB_SLUGS.get(team_id)
    return f"https://www.mlb.com/{slug}/news" if slug else GENERAL_NEWS_HUB_URL


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


@cached(ttl_seconds=GAME_DATA_TTL_SECONDS)
def get_team_season_stats(team_id: int, season: int, group: str = "hitting") -> dict:
    """Team-aggregate season stats -- the team-level analogue of
    players.get_season_stats.
    """
    resp = request_with_backoff(
        "GET",
        f"{BASE_URL}/teams/{team_id}/stats",
        params={"stats": "season", "group": group, "season": season},
    )
    resp.raise_for_status()
    stats = resp.json().get("stats", [])
    splits = stats[0].get("splits", []) if stats else []
    return splits[0]["stat"] if splits else {}


def get_team_season_series(team_id: int, metric: str, group: str, start_year: int, end_year: int) -> dict:
    """Annual team-aggregate ``metric`` values for each year in
    [start_year, end_year], skipping years with no recorded value -- the
    team-level analogue of players.get_season_series.
    """
    years: list[int] = []
    values: list[float] = []
    for year in range(start_year, end_year + 1):
        stat = get_team_season_stats(team_id, year, group).get(metric)
        if stat is None:
            continue
        try:
            values.append(float(stat))
        except (TypeError, ValueError):
            continue
        years.append(year)
    return {"years": years, "values": values}
