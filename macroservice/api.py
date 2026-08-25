"""FastAPI facade over the macroservice's domain modules.

This is a thin, optional surface: every route body is one line delegating
to a plain function in teams.py/players.py/statcast.py/news.py/
trajectories.py. The Streamlit dashboard (client.py) calls those same
functions in-process and does not depend on this app running -- this exists
so the macroservice can still be run standalone (``uvicorn macroservice.api:app``)
for any future non-Streamlit consumer.
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query

from macroservice import news, players, statcast, teams, trajectories

app = FastAPI(title="MLB Macroservice", version="1.0.0")


def _require_known_team(team_id: int) -> None:
    try:
        teams.require_known_team(team_id)
    except teams.UnknownTeamError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/teams")
def list_teams() -> list[dict]:
    return teams.TEAMS


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
