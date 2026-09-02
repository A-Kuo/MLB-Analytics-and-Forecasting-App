"""FastAPI facade over the macroservice's domain modules.

This is a thin, optional surface: every route body is one line delegating
to a plain function in teams.py/players.py/statcast.py/news.py/
trajectories.py. The Streamlit dashboard (client.py) calls those same
functions in-process and does not depend on this app running -- this exists
so the macroservice can still be run standalone (``uvicorn macroservice.api:app``)
for any future non-Streamlit consumer.
"""
from __future__ import annotations

from functools import lru_cache

from fastapi import FastAPI, HTTPException, Query
from sqlalchemy import Engine, create_engine
from sqlalchemy.pool import NullPool

from macroservice import db, insights_db, news, news_db, players, statcast, teams, trajectories

app = FastAPI(title="MLB Macroservice", version="1.0.0")


def _require_known_team(team_id: int) -> None:
    try:
        teams.require_known_team(team_id)
    except teams.UnknownTeamError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@lru_cache(maxsize=1)
def _db_engine() -> Engine:
    """Postgres engine for the two Postgres-backed routes below (insights
    leaderboards, team news) -- Streamlit-free, unlike client.py's
    st.connection-based _db_engine, since this module has no Streamlit
    runtime under it (it's the module Vercel's Python function imports
    directly, and also the standalone `uvicorn macroservice.api:app` path).

    NullPool, not SQLAlchemy's default QueuePool: a serverless function
    instance is short-lived and often invoked concurrently across many
    isolated instances, so an in-process connection pool sized for a
    long-lived server (Streamlit Cloud's model) just holds idle connections
    against Neon's own connection cap for no benefit here. The DATABASE_URL
    this reads is expected to be Neon's pooled (PgBouncer) endpoint, which
    is what actually absorbs connection churn across instances.

    Raises (surfaced by callers as a 503) when DATABASE_URL isn't
    configured -- there is no live-API fallback for either route, matching
    client.py's own "Postgres-only" contract for these two features.
    """
    database_url = db.resolve_database_url()
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")
    return create_engine(database_url, poolclass=NullPool)


def _require_db_engine() -> Engine:
    try:
        return _db_engine()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/teams")
def list_teams() -> list[dict]:
    # news_hub_url is computed here (not stored on teams.TEAMS itself) so
    # the slug-mapping logic in teams.team_news_hub_url stays the single
    # source of truth shared with the Streamlit app's app.py, rather than
    # duplicating a team_id -> slug map in the frontend too.
    return [{**team, "news_hub_url": teams.team_news_hub_url(team["id"])} for team in teams.TEAMS]


@app.get("/teams/{team_id}/roster")
def roster(team_id: int, season: int = Query(..., description="Season year, e.g. 2026")) -> list[dict]:
    _require_known_team(team_id)
    return teams.get_roster(team_id, season)


@app.get("/teams/{team_id}/schedule")
def schedule(team_id: int, season: int = Query(...)) -> list[dict]:
    _require_known_team(team_id)
    return teams.get_schedule(team_id, season)


@app.get("/players/{player_id}/game-log")
def game_log(
    player_id: int,
    season: int = Query(...),
    group: str = Query("hitting", pattern="^(hitting|pitching)$"),
) -> list[dict]:
    return players.get_game_log(player_id, season, group)


@app.get("/players/{player_id}/season-stats")
def season_stats(
    player_id: int,
    season: int = Query(...),
    group: str = Query("hitting", pattern="^(hitting|pitching)$"),
) -> dict:
    return players.get_season_stats(player_id, season, group)


@app.get("/statcast/pitcher/{player_id}")
def statcast_pitcher(player_id: int, season: int = Query(...)) -> list[dict]:
    return statcast.get_pitcher_pitches(player_id, season)


@app.get("/statcast/batter/{player_id}")
def statcast_batter(player_id: int, season: int = Query(...)) -> list[dict]:
    return statcast.get_batter_batted_balls(player_id, season)


@app.get("/news")
def news_headlines(keywords: list[str] = Query(...), limit: int = Query(10, ge=1, le=50)) -> list[dict]:
    return news.get_headlines(keywords, limit)


@app.get("/news/team")
def team_news(
    team_ids: str = Query(..., alias="teamIds", description="Comma-separated team ids, e.g. '108,109'"),
    days: int = Query(7, ge=1, le=30),
    limit: int = Query(10, ge=1, le=50),
) -> dict:
    """Team-scoped headlines from the pre-ingested Postgres cache (see
    macroservice/news_db.py / scripts/ingest_team_news.py) -- the dashboard's
    actual News Feed source on both the Streamlit app and this frontend.
    Postgres-only, no live-API fallback, matching client.get_team_news.

    Wrapped in {"data": [...]} (not a bare list) to match components/layout/
    NewsDrawer.tsx's existing fetch shape.
    """
    try:
        parsed_ids = tuple(int(tid) for tid in team_ids.split(",") if tid.strip())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="teamIds must be a comma-separated list of integers") from exc

    engine = _require_db_engine()
    rows = news_db.fetch_team_news(engine, parsed_ids, limit=limit, days=days)
    return {
        "data": [
            {
                "id": str(row["id"]),
                "headline": row["headline"],
                "source": row["source"],
                "url": row["link"],
                "thumbnail_url": row["thumbnail"],
                "published_at": row["published_at"].isoformat() if row["published_at"] else None,
            }
            for row in rows
        ]
    }


@app.get("/insights/leaderboard")
def insights_leaderboard(
    metric_key: str = Query(...),
    group: str = Query(..., pattern="^(hitting|pitching)$"),
    season: int = Query(...),
    team_ids: str = Query(..., alias="teamIds", description="Comma-separated team ids, e.g. '108,109'"),
    limit: int = Query(10, ge=1, le=50),
) -> list[dict]:
    """Top ``limit`` players for one metric/season among ``team_ids`` --
    Postgres-only (see macroservice/insights_db.py), matching
    client.get_insights_leaderboard. Coverage depends on
    scripts/backfill_season_leaderboard.py having been run for ``season``.
    """
    try:
        parsed_ids = frozenset(int(tid) for tid in team_ids.split(",") if tid.strip())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="teamIds must be a comma-separated list of integers") from exc

    engine = _require_db_engine()
    return insights_db.top_players_by_metric(engine, metric_key, group, season, parsed_ids, limit)


@app.get("/players/{player_id}/hitter-trajectory")
def hitter_trajectory(
    player_id: int,
    season: int = Query(...),
    metric: str = Query("ops", pattern="^(avg|obp|slg|ops|homeRuns|rbi|strikeOuts|baseOnBalls)$"),
) -> dict:
    return trajectories.compute_hitter_trajectory(player_id, season, metric)


@app.get("/players/{player_id}/pitcher-trajectory")
def pitcher_trajectory(
    player_id: int,
    season: int = Query(...),
    fallback_metric: str = Query("era", pattern="^(era|whip|strikeOuts|baseOnBalls|inningsPitched|earnedRuns)$"),
) -> dict:
    return trajectories.compute_pitcher_trajectory(player_id, season, fallback_metric)


@app.get("/teams/{team_id}/trajectory")
def team_trajectory(
    team_id: int,
    season: int = Query(...),
    mode: str = Query("offense", pattern="^(offense|defense)$"),
) -> dict:
    _require_known_team(team_id)
    return trajectories.compute_team_trajectory(team_id, season, mode)
