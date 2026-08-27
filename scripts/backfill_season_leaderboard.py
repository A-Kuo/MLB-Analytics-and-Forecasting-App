"""Populates the Postgres cache with everything the Insights page's
leaderboards need for one season: season-scoped team rosters
(player_season_team), player bios (players), season stats, and Statcast
season aggregates.

Run on demand, per season, before exploring that season on the Insights
page (unlike scripts/backfill_roster_history.py, this has no scheduled
workflow -- Insights is explored a season at a time, not continuously):

    python scripts/backfill_season_leaderboard.py --season 2024
    python scripts/backfill_season_leaderboard.py --season 2024 --team-id 147

Volume: ~30 teams x ~30-45 rostered players x ~2 live calls (season stats +
Statcast) plus one roster call and one bio-batch call per team -- roughly
1,800-2,700 API calls for a whole season, tractable in one run (unlike a
full-history backfill across ~125 seasons, which was ruled out as
infeasible -- see client.py's lazy self-healing caches for that scope).

Unlike client.py's lazy caches, this script WILL write rows for the
current, in-progress season if asked (Austin wants to explore in-progress
seasons too) -- such rows can go stale between manual re-runs; re-run to
refresh. Every upsert here is ON CONFLICT DO UPDATE, so re-running for the
same season is always safe.

Reads the connection string from a DATABASE_URL environment variable (or a
local .env), same as scripts/backfill_roster_history.py -- this runs
outside Streamlit entirely.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine

sys.path.insert(0, str(Path(__file__).parent.parent))

from macroservice import (  # noqa: E402  (needs the path insert above)
    db,
    insights_db,
    players,
    roster_history,
    roster_history_db,
    season_stats_db,
    statcast_season,
    teams,
)


def _backfill_player(engine, player_id: int, season: int, group: str) -> None:
    """One player's season stats + (if applicable) Statcast season
    aggregate. Isolated per player: one player's API hiccup shouldn't cost
    the rest of the team's roster their refresh.
    """
    stats = players.get_season_stats(player_id, season, group)
    if group == "pitching":
        season_stats_db.upsert_player_season_pitching(engine, player_id, season, stats)
    else:
        season_stats_db.upsert_player_season_hitting(engine, player_id, season, stats)

    if season >= statcast_season.STATCAST_ERA_START_YEAR:
        if group == "pitching":
            statcast = statcast_season.compute_pitcher_statcast_season(player_id, season)
            season_stats_db.upsert_player_statcast_pitching_season(engine, player_id, season, statcast)
        else:
            statcast = statcast_season.compute_hitter_statcast_season(player_id, season)
            season_stats_db.upsert_player_statcast_hitting_season(engine, player_id, season, statcast)


def backfill_team(engine, team_id: int, season: int) -> tuple[int, list[tuple[int, Exception]]]:
    """Backfills one team's season-scoped roster, bios, season stats, and
    Statcast aggregates. Returns (players attempted, per-player failures).
    """
    roster = teams.get_roster(team_id, season)
    if not roster:
        return 0, []

    # All-time bios (debut/last-active/active) -- the season-scoped roster
    # above has no bio fields of its own.
    bio_by_id = {p["id"]: p for p in roster_history.get_team_roster_with_active_years(team_id)}

    players_rows = [
        {
            "id": entry["id"],
            "name": bio_by_id.get(entry["id"], {}).get("name") or entry["name"],
            "debut_year": bio_by_id.get(entry["id"], {}).get("debut_year"),
            "last_active_year": bio_by_id.get(entry["id"], {}).get("last_active_year"),
            "active": bio_by_id.get(entry["id"], {}).get("active", False),
        }
        for entry in roster
    ]
    roster_history_db.upsert_players_bio(engine, players_rows)

    season_team_rows = [
        {
            "player_id": entry["id"],
            "team_id": team_id,
            "season": season,
            "position": entry["position"],
            "is_pitcher": entry["is_pitcher"],
        }
        for entry in roster
    ]
    insights_db.upsert_player_season_team(engine, season_team_rows)

    failures: list[tuple[int, Exception]] = []
    for entry in roster:
        group = "pitching" if entry["is_pitcher"] else "hitting"
        try:
            _backfill_player(engine, entry["id"], season, group)
        except Exception as exc:  # noqa: BLE001  (any failure is per-player recoverable)
            failures.append((entry["id"], exc))
    return len(roster), failures


def backfill(engine, team_ids: list[int], season: int) -> list[tuple[int, Exception]]:
    """Backfills every requested team for one season, returning whatever
    failed at the team level. Per-team isolation: one team's roster fetch
    failing shouldn't cost the other 29 their refresh.
    """
    team_failures: list[tuple[int, Exception]] = []
    for index, team_id in enumerate(team_ids, start=1):
        name = teams.TEAM_BY_ID.get(team_id, {}).get("name", team_id)
        print(f"[{index}/{len(team_ids)}] {name}...", flush=True)
        try:
            attempted, player_failures = backfill_team(engine, team_id, season)
            print(f"    {attempted - len(player_failures)}/{attempted} players", flush=True)
            for player_id, exc in player_failures:
                print(f"    player {player_id} FAILED: {exc}", flush=True)
        except Exception as exc:  # noqa: BLE001  (any failure is per-team recoverable)
            print(f"    FAILED: {exc}", flush=True)
            team_failures.append((team_id, exc))
    return team_failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, required=True, help="Season to backfill, e.g. 2024")
    parser.add_argument("--team-id", type=int, help="Backfill only this team (default: all 30)")
    args = parser.parse_args()

    load_dotenv()
    database_url = db.resolve_database_url()
    if not database_url:
        print(
            "No database connection string found -- set DATABASE_URL (environment or .env), "
            "or configure [connections.postgresql].url in .streamlit/secrets.toml.",
            file=sys.stderr,
        )
        return 2

    team_ids = [args.team_id] if args.team_id else [team["id"] for team in teams.TEAMS]

    engine = create_engine(database_url)
    db.ensure_schema(engine)
    failures = backfill(engine, team_ids, args.season)

    succeeded = len(team_ids) - len(failures)
    print(f"\n{succeeded}/{len(team_ids)} teams backfilled for season {args.season}.")
    if failures:
        # Non-zero exit so a broken run is visible even when most teams
        # succeeded -- a silent partial refresh is worse than a visible one.
        print("Failed: " + ", ".join(str(team_id) for team_id, _ in failures), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
