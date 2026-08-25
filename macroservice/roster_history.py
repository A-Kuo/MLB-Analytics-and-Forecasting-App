"""All-time roster history and date-range player resolution.

Backs the player selector's "(active years)" annotations, the portrait
wall, and the Offense/Defense/All-Players bulk-selection checkboxes --
all of which need to know which players were ever on a team across an
arbitrary year range, not just one season's snapshot roster
(macroservice.teams.get_roster).
"""
from __future__ import annotations

from macroservice.backoff import request_with_backoff
from macroservice.caching import cached

BASE_URL = "https://statsapi.mlb.com/api/v1"
ALLTIME_ROSTER_TTL_SECONDS = 24 * 60 * 60  # franchise history changes rarely
PEOPLE_BATCH_TTL_SECONDS = 24 * 60 * 60

# /people?personIds= fails on URL length, not id count: confirmed live at
# 800 ids (~7.2KB URL) -> 200, 900 ids (~8.1KB) -> 400, 1000+ -> 414 URI Too
# Long. 500 leaves comfortable margin. Some franchises' all-time rosters are
# large enough that this matters in practice (Yankees: 1850 players).
PEOPLE_BATCH_CHUNK_SIZE = 500


@cached(ttl_seconds=ALLTIME_ROSTER_TTL_SECONDS)
def get_alltime_roster(team_id: int) -> list[dict]:
    """Every player who has ever been on this team's roster, in one API
    call (rosterType=allTime) rather than looping per season -- no such
    per-season loop can express "all time" anyway, since MLB Stats API has
    no season-range roster parameter (confirmed: startSeason/endSeason are
    silently ignored). No debut/active-years info here; see
    get_team_roster_with_active_years.
    """
    resp = request_with_backoff("GET", f"{BASE_URL}/teams/{team_id}/roster", params={"rosterType": "allTime"})
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


def _chunked(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


@cached(ttl_seconds=PEOPLE_BATCH_TTL_SECONDS)
def _get_people_batch(person_ids: tuple[int, ...]) -> dict[int, dict]:
    """Bulk /people?personIds= lookup, chunked to stay under the API's
    URL-length ceiling. Returns {person_id: {"debut_year", "last_active_year",
    "active"}}. ``last_active_year`` is None while a player is still active
    -- lastPlayedDate is simply absent from the API response then, not null.
    """
    result: dict[int, dict] = {}
    for batch in _chunked(list(person_ids), PEOPLE_BATCH_CHUNK_SIZE):
        resp = request_with_backoff(
            "GET", f"{BASE_URL}/people", params={"personIds": ",".join(str(pid) for pid in batch)}
        )
        resp.raise_for_status()
        for person in resp.json().get("people", []):
            debut = person.get("mlbDebutDate")
            last_played = person.get("lastPlayedDate")
            result[person["id"]] = {
                "debut_year": int(debut[:4]) if debut else None,
                "last_active_year": int(last_played[:4]) if last_played else None,
                "active": bool(person.get("active", False)),
            }
    return result


def _active_years_label(bio: dict) -> str:
    if bio["debut_year"] is None:
        return ""
    end = "present" if bio["last_active_year"] is None else str(bio["last_active_year"])
    return f"{bio['debut_year']}–{end}"


def get_team_roster_with_active_years(team_id: int) -> list[dict]:
    """get_alltime_roster() entries enriched with debut_year/
    last_active_year/active/active_years_label -- backs both the roster
    selector's "(active years)" suffix and resolve_players_in_range below.
    """
    roster = get_alltime_roster(team_id)
    bios = _get_people_batch(tuple(entry["id"] for entry in roster))
    enriched = []
    for entry in roster:
        bio = bios.get(entry["id"], {"debut_year": None, "last_active_year": None, "active": False})
        enriched.append({**entry, **bio, "active_years_label": _active_years_label(bio)})
    return enriched


def resolve_players_in_range(team_id: int, start_year: int, end_year: int, group: str | None = None) -> set[int]:
    """Player ids whose [debut_year, last_active_year-or-now] overlaps
    [start_year, end_year] -- the resolver behind the Offense/Defense/All
    Players bulk-selection checkboxes, evaluated against the dashboard's
    timeline range rather than a single season.

    group="hitting"|"pitching" filters by position; None returns everyone.
    A player with no known debut_year (data gap) is excluded rather than
    guessed at.
    """
    roster = get_team_roster_with_active_years(team_id)
    matched: set[int] = set()
    for entry in roster:
        if entry["debut_year"] is None:
            continue
        if group == "hitting" and entry["is_pitcher"]:
            continue
        if group == "pitching" and not entry["is_pitcher"]:
            continue
        last_year = entry["last_active_year"] if entry["last_active_year"] is not None else end_year
        if entry["debut_year"] <= end_year and last_year >= start_year:
            matched.add(entry["id"])
    return matched
