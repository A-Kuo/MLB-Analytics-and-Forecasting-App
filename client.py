"""Thin HTTP client for the MLB data service, with Streamlit-aware caching.

The dashboard never calls the MLB Stats API, Baseball Savant, or a news
source directly -- every external fact comes from the data service, so the
caching, retries, and rate-limit handling live in one place.
"""
from __future__ import annotations

import os

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

DATA_SERVICE_URL = os.getenv("DATA_SERVICE_URL", "http://localhost:8000")
REQUEST_TIMEOUT_SECONDS = 30


def _get(path: str, params: dict | None = None):
    resp = requests.get(f"{DATA_SERVICE_URL}{path}", params=params, timeout=REQUEST_TIMEOUT_SECONDS)
    resp.raise_for_status()
    return resp.json()


@st.cache_data(ttl=3600)
def get_teams() -> list[dict]:
    return _get("/teams")


@st.cache_data(ttl=3600)
def get_roster(team_id: int, season: int) -> list[dict]:
    return _get(f"/teams/{team_id}/roster", params={"season": season})


@st.cache_data(ttl=60)
def get_season_stats(player_id: int, season: int, group: str) -> dict:
    return _get(f"/players/{player_id}/season-stats", params={"season": season, "group": group})


@st.cache_data(ttl=60)
def get_game_log_splits(player_id: int, season: int, group: str) -> list[dict]:
    return _get(f"/players/{player_id}/game-log", params={"season": season, "group": group})


@st.cache_data(ttl=300)
def get_hitter_trajectory(player_id: int, season: int, metric: str) -> dict:
    return _get(f"/players/{player_id}/hitter-trajectory", params={"season": season, "metric": metric})


@st.cache_data(ttl=300)
def get_pitcher_trajectory(player_id: int, season: int, fallback_metric: str = "era") -> dict:
    return _get(
        f"/players/{player_id}/pitcher-trajectory",
        params={"season": season, "fallback_metric": fallback_metric},
    )


@st.cache_data(ttl=300)
def get_team_trajectory(team_id: int, season: int, mode: str) -> dict:
    return _get(f"/teams/{team_id}/trajectory", params={"season": season, "mode": mode})


@st.cache_data(ttl=300)
def get_news(keywords: list[str], limit: int = 10) -> list[dict]:
    return _get("/news", params={"keywords": keywords, "limit": limit})
