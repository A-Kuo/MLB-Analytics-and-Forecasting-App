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

from macroservice import roster_history, roster_history_db, teams  # noqa: E402  (needs the path insert above)


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
    parser.add_argument("--team-id", type=int, help="Backfill only this team (default: all 30)")
    args = parser.parse_args()

    load_dotenv()
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL is not set (expected in the environment or a local .env).", file=sys.stderr)
        return 2

    team_ids = [args.team_id] if args.team_id else [team["id"] for team in teams.TEAMS]

    engine = create_engine(database_url)
    roster_history_db.ensure_schema(engine)
    failures = backfill(engine, team_ids)

    succeeded = len(team_ids) - len(failures)
    print(f"\n{succeeded}/{len(team_ids)} teams backfilled.")
    if failures:
        # Non-zero exit so a scheduled CI run surfaces as failed even when
        # most teams succeeded -- a silent partial refresh is worse than a
        # visible one.
        print("Failed: " + ", ".join(str(team_id) for team_id, _ in failures), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
