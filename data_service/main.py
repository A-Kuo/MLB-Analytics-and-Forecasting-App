"""MLB data service: a REST API in front of the MLB Stats API, Baseball
Savant Statcast, and MLB news RSS, so consuming applications never call
those upstreams directly. Every outbound call goes through backoff.py's
exponential backoff wrapper to respect upstream rate limits.
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query

from clients import mlb_client, news_client, statcast_client

app = FastAPI(title="MLB Data Service", version="1.0.0")

TEAMS_PATH = Path(__file__).parent / "config" / "teams.json"
TEAMS: list[dict] = json.loads(TEAMS_PATH.read_text())
TEAM_BY_ID: dict[int, dict] = {team["id"]: team for team in TEAMS}


def _require_known_team(team_id: int) -> None:
    if team_id not in TEAM_BY_ID:
        raise HTTPException(status_code=404, detail=f"Unknown team_id {team_id}")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/teams")
def list_teams() -> list[dict]:
    return TEAMS


@app.get("/teams/{team_id}/roster")
def roster(team_id: int, season: int = Query(..., description="Season year, e.g. 2026")) -> list[dict]:
    _require_known_team(team_id)
    return mlb_client.get_roster(team_id, season)


@app.get("/teams/{team_id}/schedule")
def schedule(team_id: int, season: int = Query(...)) -> list[dict]:
    _require_known_team(team_id)
    return mlb_client.get_schedule(team_id, season)


@app.get("/players/{player_id}/game-log")
def game_log(
    player_id: int,
    season: int = Query(...),
    group: str = Query("hitting", pattern="^(hitting|pitching)$"),
) -> list[dict]:
    return mlb_client.get_game_log(player_id, season, group)


@app.get("/players/{player_id}/season-stats")
def season_stats(
    player_id: int,
    season: int = Query(...),
    group: str = Query("hitting", pattern="^(hitting|pitching)$"),
) -> dict:
    return mlb_client.get_season_stats(player_id, season, group)


@app.get("/statcast/pitcher/{player_id}")
def statcast_pitcher(player_id: int, season: int = Query(...)) -> list[dict]:
    return statcast_client.get_pitcher_pitches(player_id, season)


@app.get("/statcast/batter/{player_id}")
def statcast_batter(player_id: int, season: int = Query(...)) -> list[dict]:
    return statcast_client.get_batter_batted_balls(player_id, season)


@app.get("/news")
def news(keywords: list[str] = Query(...), limit: int = Query(10, ge=1, le=50)) -> list[dict]:
    return news_client.get_headlines(keywords, limit)
