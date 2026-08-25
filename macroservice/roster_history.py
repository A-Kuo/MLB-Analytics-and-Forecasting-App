"""All-time roster history and date-range player resolution.

Backs the player selector's "(active years)" annotations, the portrait
wall, and the position-group bulk-selection checkboxes --
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

    ``positions`` is a list rather than a single value so a future
    multi-position data source needs no shape change here -- but this
    endpoint returns exactly one roster entry per person (confirmed live),
    so it's always a single-element list today. Generic "OF" (outfielder
    with no LF/CF/RF specificity, ~11 entries across all-time rosters) is
    normalized to all three outfield positions so they match the
    position-checkbox filters.
    """
    resp = request_with_backoff("GET", f"{BASE_URL}/teams/{team_id}/roster", params={"rosterType": "allTime"})
    resp.raise_for_status()
    roster = resp.json().get("roster", [])
    result = []
    for entry in roster:
        pos = entry["position"]["abbreviation"]
        # Normalize generic "OF" to all three specific positions so they
        # surface under any outfield position filter (LF/CF/RF).
        positions = ["LF", "CF", "RF"] if pos == "OF" else [pos]
        result.append(
            {
                "id": entry["person"]["id"],
                "name": entry["person"]["fullName"],
                "positions": positions,
                "is_pitcher": pos == "P",
            }
        )
    return result


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


def _active_year_ranges(bio: dict) -> list[tuple[int, int | None]]:
    if bio["debut_year"] is None:
        return []
    return [(bio["debut_year"], bio["last_active_year"])]


def _active_years_label(ranges: list[tuple[int, int | None]]) -> str:
    if not ranges:
        return ""
    return ", ".join(f"{start}–{'present' if end is None else end}" for start, end in ranges)


def get_team_roster_with_active_years(team_id: int) -> list[dict]:
    """get_alltime_roster() entries enriched with debut_year/
    last_active_year/active/active_year_ranges/active_years_label -- backs
    both the roster selector's "(active years)" suffix and
    resolve_players_in_range below.

    ``active_year_ranges`` is a list of (start, end) spans rather than a
    single one, so a player who left this team's roster and later returned
    would render correctly -- but MLB Stats API only exposes one
    career-wide debut/last-played date per person (not per team stint), so
    every entry here has exactly one span today.
    """
    roster = get_alltime_roster(team_id)
    bios = _get_people_batch(tuple(entry["id"] for entry in roster))
    enriched = []
    for entry in roster:
        bio = bios.get(entry["id"], {"debut_year": None, "last_active_year": None, "active": False})
        ranges = _active_year_ranges(bio)
        enriched.append(
            {**entry, **bio, "active_year_ranges": ranges, "active_years_label": _active_years_label(ranges)}
        )
    return enriched


def resolve_players_in_range(
    team_id: int, start_year: int, end_year: int, positions: frozenset[str] | None = None
) -> set[int]:
    """Player ids whose [debut_year, last_active_year-or-now] overlaps
    [start_year, end_year] -- the resolver behind the position-group
    bulk-selection checkboxes, evaluated against the dashboard's timeline
    range rather than a single season.

    ``positions``, when given, keeps only players holding at least one of
    those position acronyms (e.g. {"1B", "2B", "3B", "SS"} for "Infield");
    None returns everyone. A player with no known debut_year (data gap) is
    excluded rather than guessed at.
    """
    roster = get_team_roster_with_active_years(team_id)
    matched: set[int] = set()
    for entry in roster:
        if entry["debut_year"] is None:
            continue
        if positions is not None and not (set(entry["positions"]) & positions):
            continue
        last_year = entry["last_active_year"] if entry["last_active_year"] is not None else end_year
        if entry["debut_year"] <= end_year and last_year >= start_year:
            matched.add(entry["id"])
    return matched
