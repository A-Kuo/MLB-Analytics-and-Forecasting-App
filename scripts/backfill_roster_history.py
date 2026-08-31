"""Populates the Postgres roster-history cache from the MLB Stats API.

Run on a schedule by .github/workflows/backfill_roster_history.yml (roster
data changes only a few times a year), or manually:

    python scripts/backfill_roster_history.py
    python scripts/backfill_roster_history.py --team-id 109

Reads the connection string from a DATABASE_URL environment variable (or a
local .env, same as NEWS_API_KEY) rather than st.secrets -- this runs
outside Streamlit entirely, in CI or a terminal.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine

sys.path.insert(0, str(Path(__file__).parent.parent))

from macroservice import db, roster_history, roster_history_db, teams  # noqa: E402  (needs the path insert above)


def backfill(engine, team_ids: list[int]) -> list[tuple[int, Exception]]:
    """Fetches and stores each team's all-time roster, returning whatever
    failed. Per-team isolation matters: one team's API hiccup shouldn't
    cost the other 29 their refresh.
    """
    failures: list[tuple[int, Exception]] = []
    for index, team_id in enumerate(team_ids, start=1):
        name = teams.TEAM_BY_ID.get(team_id, {}).get("name", team_id)
        print(f"[{index}/{len(team_ids)}] {name}...", flush=True)
        try:
            roster = roster_history.get_team_roster_with_active_years(team_id)
            roster_history_db.upsert_team_roster(engine, team_id, roster)
            print(f"    {len(roster)} players", flush=True)
        except Exception as exc:  # noqa: BLE001  (any failure is per-team recoverable)
            print(f"    FAILED: {exc}", flush=True)
            failures.append((team_id, exc))
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--start-year",
        type=int,
        help=(
            "Optional workflow scope label. The roster cache remains all-time "
            "and uses runtime timeline filtering."
        ),
    )
    parser.add_argument(
        "--end-year",
        type=int,
        help=(
            "Optional workflow scope label. The roster cache remains all-time "
            "and uses runtime timeline filtering."
        ),
    )
    args = parser.parse_args()

    if (args.start_year is None) != (args.end_year is None):
        parser.error("--start-year and --end-year must be supplied together.")

    if args.start_year is not None and args.start_year > args.end_year:
        parser.error("--start-year cannot be later than --end-year.")

    if args.start_year is not None:
        print(
            f"Requested roster-history workflow scope: "
            f"{args.start_year}-{args.end_year}.",
            flush=True,
        )

    load_dotenv()
    database_url = db.resolve_database_url()
    if not database_url:
        print(
            "No database connection string found -- set DATABASE_URL (environment or .env), "
            "or configure [connections.postgresql].url in .streamlit/secrets.toml.",
            file=sys.stderr,
        )
        return 2

    # Always process every configured team.
    team_ids = [team["id"] for team in teams.TEAMS]

    engine = create_engine(database_url)
    db.ensure_schema(engine)
    failures = backfill(engine, team_ids)

    succeeded = len(team_ids) - len(failures)
    print(f"\n{succeeded}/{len(team_ids)} teams backfilled.")

    if failures:
        print(
            "Failed: " + ", ".join(str(team_id) for team_id, _ in failures),
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
