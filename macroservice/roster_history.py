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
        person = entry["person"]
        result.append(
            {
                "id": person["id"],
                # A handful of all-time roster entries carry only an id and
                # link, with no fullName (confirmed live: Dodgers person
                # 116751, who /people returns nothing for either -- an
                # orphaned record on MLB's side). Falling back to a
                # placeholder keeps one bad row from failing a whole team's
                # roster; such a player has no bio, so no active-year span,
                # so resolve_from_roster never surfaces them in the UI.
                "name": person.get("fullName") or f"Unknown Player {person['id']}",
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
    """A missing `last_active_year` means "still active" ONLY when the
    API's own `active` flag confirms it -- a retired player from before
    the API consistently tracked lastPlayedDate (a real data gap, common
    for 19th/early-20th-century players) also has `last_active_year: None`
    but `active: False`, and must not be treated as playing today. Such a
    player falls back to a single-season span at their debut year rather
    than being projected forward indefinitely.
    """
    if bio["debut_year"] is None:
        return []
    if bio["last_active_year"] is not None:
        return [(bio["debut_year"], bio["last_active_year"])]
    if bio["active"]:
        return [(bio["debut_year"], None)]
    return [(bio["debut_year"], bio["debut_year"])]


def _active_years_label(ranges: list[tuple[int, int | None]]) -> str:
    if not ranges:
        return ""
    return ", ".join(f"{start}–{'present' if end is None else end}" for start, end in ranges)


def active_years_label(debut_year: int | None, last_active_year: int | None, active: bool) -> str:
    """Public entry point for the "years active" display string, reusing
    the corrected _active_year_ranges logic -- for callers outside this
    module (e.g. macroservice/insights_db.py) that only have raw bio
    fields, not a full roster row.
    """
    ranges = _active_year_ranges({"debut_year": debut_year, "last_active_year": last_active_year, "active": active})
    return _active_years_label(ranges)


def enrich_with_active_years(rows: list[dict]) -> list[dict]:
    """Attaches active_year_ranges/active_years_label to bio+stint rows --
    each row needs id/name/positions/is_pitcher/debut_year/last_active_year/
    active. Shared by both the live-API path (get_team_roster_with_active_years
    below) and the Postgres-backed path (macroservice/roster_history_db.py),
    so the "corrected last-active-year" fix in _active_year_ranges lives in
    exactly one place regardless of where the raw row data came from.
    """
    enriched = []
    for row in rows:
        ranges = _active_year_ranges(row)
        enriched.append({**row, "active_year_ranges": ranges, "active_years_label": _active_years_label(ranges)})
    return enriched


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
    rows = [
        {**entry, **bios.get(entry["id"], {"debut_year": None, "last_active_year": None, "active": False})}
        for entry in roster
    ]
    return enrich_with_active_years(rows)


def resolve_from_roster(
    roster: list[dict], start_year: int, end_year: int, positions: frozenset[str] | None = None
) -> set[int]:
    """Player ids (from an already-fetched roster -- see
    get_team_roster_with_active_years/macroservice.roster_history_db) with
    at least one active-year span overlapping [start_year, end_year].

    ``positions``, when given, keeps only players holding at least one of
    those position acronyms (e.g. {"1B", "2B", "3B", "SS"} for "Infield");
    None returns everyone. A player with no known debut_year (data gap)
    has no spans (see _active_year_ranges) and is never matched.
    """
    matched: set[int] = set()
    for entry in roster:
        if positions is not None and not (set(entry["positions"]) & positions):
            continue
        for span_start, span_end in entry["active_year_ranges"]:
            resolved_end = end_year if span_end is None else span_end
            if span_start <= end_year and resolved_end >= start_year:
                matched.add(entry["id"])
                break
    return matched


def resolve_players_in_range(
    team_id: int, start_year: int, end_year: int, positions: frozenset[str] | None = None
) -> set[int]:
    """The resolver behind the position checkboxes, evaluated against the
    dashboard's timeline range rather than a single season -- see
    resolve_from_roster for the matching rule.
    """
    roster = get_team_roster_with_active_years(team_id)
    return resolve_from_roster(roster, start_year, end_year, positions)
