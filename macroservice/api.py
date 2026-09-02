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
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.pool import NullPool

from macroservice import db, insights_db, news, news_db, players, statcast, teams, trajectories
from utils.aggregation import aggregate_scalar, aggregate_series
from utils.filters import is_mean_aggregated

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


# metric key -> (table, column) -- same mapping as lib/db/analytics.ts's
# registries (kept in sync manually; see that file's own comment).
_HITTING_COLUMNS: dict[str, tuple[str, str]] = {
    "avg": ("player_season_hitting_stats", "avg"),
    "obp": ("player_season_hitting_stats", "obp"),
    "slg": ("player_season_hitting_stats", "slg"),
    "ops": ("player_season_hitting_stats", "ops"),
    "homeRuns": ("player_season_hitting_stats", "home_runs"),
    "rbi": ("player_season_hitting_stats", "rbi"),
    "strikeOuts": ("player_season_hitting_stats", "strikeouts"),
    "baseOnBalls": ("player_season_hitting_stats", "walks"),
    "xba": ("player_statcast_hitting_season", "xba"),
    "avgExitVelocity": ("player_statcast_hitting_season", "avg_exit_velocity"),
    "hardHitPct": ("player_statcast_hitting_season", "hard_hit_pct"),
    "barrelPct": ("player_statcast_hitting_season", "barrel_pct"),
}
_PITCHING_COLUMNS: dict[str, tuple[str, str]] = {
    "era": ("player_season_pitching_stats", "era"),
    "whip": ("player_season_pitching_stats", "whip"),
    "strikeOuts": ("player_season_pitching_stats", "strikeouts"),
    "baseOnBalls": ("player_season_pitching_stats", "walks"),
    "inningsPitched": ("player_season_pitching_stats", "innings_pitched"),
    "earnedRuns": ("player_season_pitching_stats", "earned_runs"),
    "cswPct": ("player_statcast_pitching_season", "csw_pct"),
    "whiffPct": ("player_statcast_pitching_season", "whiff_pct"),
    "chasePct": ("player_statcast_pitching_season", "chase_pct"),
    "avgVelocity": ("player_statcast_pitching_season", "avg_velocity"),
}


def _get_player_series(player_id: int, metric: str, group: str, start_year: int, end_year: int, engine: Engine | None) -> dict:
    """One bulk range query per player/metric -- Postgres-only, no live-API
    fallback, matching lib/db/analytics.ts's approach exactly (and Insights'
    own Postgres-only convention). A per-year loop with a live-API fallback
    on every miss was the original approach here; for the wide default
    range this page starts with (EARLIEST_SEASON..current year, ~125
    seasons), that meant up to ~125 live MLB Stats API calls for a single
    player -- confirmed directly to hang for well over a minute. A season
    genuinely not yet in Postgres is treated as "no data for that year"
    rather than fetched live, the same tradeoff Insights leaderboards
    already make for the same reason.
    """
    if engine is None:
        return {"years": [], "values": []}
    columns = _PITCHING_COLUMNS if group == "pitching" else _HITTING_COLUMNS
    table, column = columns[metric]
    sql = text(f"""
        SELECT season, {column} AS value
        FROM {table}
        WHERE player_id = :player_id AND season BETWEEN :start_year AND :end_year AND {column} IS NOT NULL
        ORDER BY season
    """)
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                sql, {"player_id": player_id, "start_year": start_year, "end_year": end_year}
            ).mappings().all()
    except Exception:
        return {"years": [], "values": []}
    return {"years": [row["season"] for row in rows], "values": [row["value"] for row in rows]}


@app.get("/analytics/kpi")
def aggregate_kpi(
    player_ids: str = Query(..., alias="playerIds"),
    metric: str = Query(...),
    group: str = Query(..., pattern="^(hitting|pitching)$"),
    start_year: int = Query(..., alias="startYear"),
    end_year: int = Query(..., alias="endYear"),
) -> dict:
    """Fallback/reference implementation of the aggregate KPI -- the
    Next.js frontend's primary path is the pure-SQL lib/db/analytics.ts
    (one aggregate query, no per-player Python loop), kept for parity and
    any non-Vercel consumer of this standalone API.
    """
    try:
        engine = _db_engine()
    except RuntimeError:
        engine = None
    ids = [int(pid) for pid in player_ids.split(",") if pid.strip()]
    series_by_player = {pid: _get_player_series(pid, metric, group, start_year, end_year, engine) for pid in ids}
    return {"value": aggregate_scalar(series_by_player, is_mean_aggregated(metric))}


@app.get("/forecast/aggregate")
def aggregate_forecast(
    player_ids: str = Query(..., alias="playerIds"),
    metric: str = Query(...),
    group: str = Query(..., pattern="^(hitting|pitching)$"),
    train_start: int = Query(..., alias="trainStart"),
    train_end: int = Query(..., alias="trainEnd"),
    forecast_end: int = Query(..., alias="forecastEnd"),
) -> dict:
    """Aggregate multi-player forecast -- fits the same SVR+Huber+Gaussian
    Process ensemble Streamlit uses (trajectories.compute_forecast_from_series),
    combining every selected player's own series first (sum for counting
    stats, mean for rate stats -- utils.aggregation.aggregate_series).

    This is the one Analytics-page feature that can't be a pure-SQL
    Next.js route like KPI/Trend: the regression ensemble has no faithful
    JS equivalent, and it must fit fresh for whatever arbitrary player
    combination is currently selected, not a fixed, precomputable subject.
    The latency lever here is avoiding N live MLB API calls for training
    data that's already cached -- see _get_player_season_stat -- rather
    than avoiding the fit itself.
    """
    try:
        engine = _db_engine()
    except RuntimeError:
        engine = None
    ids = [int(pid) for pid in player_ids.split(",") if pid.strip()]

    def get_series(series_metric: str, series_group: str, start_year: int, end_year: int) -> dict:
        series_by_player = {
            pid: _get_player_series(pid, series_metric, series_group, start_year, end_year, engine) for pid in ids
        }
        return aggregate_series(series_by_player, is_mean_aggregated(series_metric))

    return trajectories.compute_forecast_from_series(get_series, metric, group, train_start, train_end, forecast_end)


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
