"""Populates the Postgres team_news cache from MLB.com's and SB Nation's
per-team feeds (see macroservice/config/news_sources.py for the full
source-verification record -- only these two sources are implemented).

Run on a schedule by .github/workflows/ingest_team_news.yml (every 6
hours -- news changes constantly, unlike roster/season data), or manually:

    python scripts/ingest_team_news.py
    python scripts/ingest_team_news.py --team-id 147

This moves news fetching off the Streamlit request path entirely --
client.get_team_news reads only from the table this script writes, with no
live-API fallback (see macroservice/news_db.py). Reads the connection
string from a DATABASE_URL environment variable (or a local .env), same as
scripts/backfill_roster_history.py -- this runs outside Streamlit entirely.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine

sys.path.insert(0, str(Path(__file__).parent.parent))

from macroservice import db, news, news_db, teams  # noqa: E402  (needs the path insert above)

DEFAULT_LOOKBACK_DAYS = 7


def ingest(engine, team_ids: list[int]) -> list[tuple[int, Exception]]:
    """Fetches and upserts each team's news, returning whatever failed.
    Per-team isolation: one team's feed hiccup shouldn't cost the other 29
    their refresh.
    """
    failures: list[tuple[int, Exception]] = []
    for index, team_id in enumerate(team_ids, start=1):
        name = teams.TEAM_BY_ID.get(team_id, {}).get("name", team_id)
        print(f"[{index}/{len(team_ids)}] {name}...", flush=True)
        try:
            articles = news.fetch_team_articles(team_id, DEFAULT_LOOKBACK_DAYS)
            rows = [{**article, "team_id": team_id} for article in articles]
            news_db.upsert_team_news(engine, rows)
            print(f"    {len(rows)} articles", flush=True)
        except Exception as exc:  # noqa: BLE001  (any failure is per-team recoverable)
            print(f"    FAILED: {exc}", flush=True)
            failures.append((team_id, exc))
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--team-id", type=int, help="Ingest only this team (default: all 30)")
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
    failures = ingest(engine, team_ids)
    news_db.delete_stale_news(engine, DEFAULT_LOOKBACK_DAYS)

    succeeded = len(team_ids) - len(failures)
    print(f"\n{succeeded}/{len(team_ids)} teams ingested.")
    if failures:
        # Non-zero exit so a scheduled CI run surfaces as failed even when
        # most teams succeeded -- a silent partial refresh is worse than a
        # visible one.
        print("Failed: " + ", ".join(str(team_id) for team_id, _ in failures), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
