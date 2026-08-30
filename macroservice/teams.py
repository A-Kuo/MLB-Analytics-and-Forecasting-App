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

# Map team_id -> verified news hub slug where MLB.com has one;
# teams not in this dict fall back to GENERAL_NEWS_HUB_URL via .get()
# in team_news_hub_url below.
_TEAM_NEWS_SLUGS: dict[int, str] = {
    # e.g. 147: "yankees", 111: "redsox", ...
    # fill in verified slugs as you confirm them
}


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

# The founding / debut season for each franchise in the modern MLB era (or AL/NL entry).
# Used to filter out expansion teams when backfilling historical seasons prior to their founding before addressing historical names.
FRANCHISE_ESTABLISHED_YEAR: dict[int, int] = {
    108: 1961,  # Los Angeles Angels
    109: 1998,  # Arizona Diamondbacks
    110: 1901,  # Baltimore Orioles (orig. Milwaukee Brewers 1901 -> St. Louis Browns 1902-1953)
    111: 1901,  # Boston Red Sox (Boston Americans)
    112: 1876,  # Chicago Cubs
    113: 1882,  # Cincinnati Reds
    114: 1901,  # Cleveland Guardians (Blues/Bronchos/Naps/Indians)
    115: 1993,  # Colorado Rockies
    116: 1901,  # Detroit Tigers
    117: 1962,  # Houston Astros (Colt .45s)
    118: 1969,  # Kansas City Royals
    119: 1884,  # Los Angeles Dodgers (Brooklyn Atlantics/Bridegrooms/Superbas/Robins/Dodgers)
    120: 1969,  # Washington Nationals (Montreal Expos 1969-2004)
    121: 1962,  # New York Mets
    133: 1901,  # Athletics (Philadelphia -> Kansas City -> Oakland)
    134: 1882,  # Pittsburgh Pirates
    135: 1969,  # San Diego Padres
    136: 1977,  # Seattle Mariners
    137: 1883,  # San Francisco Giants (New York Gothams/Giants)
    138: 1882,  # St. Louis Cardinals
    139: 1998,  # Tampa Bay Rays (Devil Rays)
    140: 1961,  # Texas Rangers (Washington Senators 1961-1971)
    141: 1977,  # Toronto Blue Jays
    142: 1901,  # Minnesota Twins (Washington Senators 1901-1960)
    143: 1883,  # Philadelphia Phillies
    144: 1876,  # Atlanta Braves (Boston Red Stockings/Braves -> Milwaukee Braves)
    145: 1901,  # Chicago White Sox
    146: 1993,  # Miami Marlins (Florida Marlins)
    147: 1901,  # New York Yankees (orig. Baltimore Orioles 1901-1902 -> NY Highlanders 1903-1912)
    158: 1969,  # Milwaukee Brewers (orig. Seattle Pilots 1969)
}


def is_team_active_in_season(team_id: int, season: int) -> bool:
    """True if the franchise existed and played in the given season."""
    established = FRANCHISE_ESTABLISHED_YEAR.get(team_id, 1901)
    return season >= established


def team_news_hub_url(team_id: int) -> str:
    """The team's dedicated news hub, falling back to the general MLB.com
    hub for any id not in TEAM_NEWS_HUB_SLUGS (defensive -- every team
    known today has a verified slug, see above).
    """
    slug = TEAM_NEWS_HUB_SLUGS.get(team_id)
    return f"https://www.mlb.com/{slug}/news" if slug else GENERAL_NEWS_HUB_URL


def team_news_rss_url(team_id: int) -> str | None:
    """The team's dedicated MLB.com RSS feed (confirmed live: every team's
    news hub has a feed at this exact URL shape, mirroring the general
    feed's own https://www.mlb.com/feeds/news/rss.xml). Returns None for
    any id not in TEAM_NEWS_HUB_SLUGS (defensive -- every team known today
    has a verified slug) -- unlike team_news_hub_url, there's no general
    fallback here, since a caller wanting an all-teams feed should use the
    keyword-filtered macroservice.news.get_headlines path instead.
    """
    slug = TEAM_NEWS_HUB_SLUGS.get(team_id)
    return f"https://www.mlb.com/{slug}/feeds/news/rss.xml" if slug else None


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
