"""Streamlit-facing facade over the macroservice's domain modules.

Calls macroservice functions directly, in-process -- no HTTP hop. Each
function keeps its own @st.cache_data layer on top of the macroservice's
internal TTLCache (macroservice.caching): the two serve different purposes
(st.cache_data is Streamlit's rerun-aware cache; the macroservice's TTLCache
still applies when macroservice.api is run standalone, without Streamlit in
front of it), so both are intentional, not redundant.
"""
from __future__ import annotations

import streamlit as st

from macroservice import news, players, teams, trajectories


@st.cache_data(ttl=3600)
def get_teams() -> list[dict]:
    return teams.TEAMS


@st.cache_data(ttl=3600)
def get_roster(team_id: int, season: int) -> list[dict]:
    return teams.get_roster(team_id, season)


def get_headshot_url(player_id: int, width: int = 213) -> str:
    return players.headshot_url(player_id, width)


@st.cache_data(ttl=60)
def get_season_stats(player_id: int, season: int, group: str) -> dict:
    return players.get_season_stats(player_id, season, group)


@st.cache_data(ttl=60)
def get_game_log_splits(player_id: int, season: int, group: str) -> list[dict]:
    return players.get_game_log(player_id, season, group)


@st.cache_data(ttl=300)
def get_hitter_trajectory(player_id: int, season: int, metric: str) -> dict:
    return trajectories.compute_hitter_trajectory(player_id, season, metric)


@st.cache_data(ttl=300)
def get_pitcher_trajectory(player_id: int, season: int, fallback_metric: str = "era") -> dict:
    return trajectories.compute_pitcher_trajectory(player_id, season, fallback_metric)


@st.cache_data(ttl=300)
def get_team_trajectory(team_id: int, season: int, mode: str) -> dict:
    return trajectories.compute_team_trajectory(team_id, season, mode)


@st.cache_data(ttl=300)
def get_news(keywords: list[str], limit: int = 10) -> list[dict]:
    return news.get_headlines(keywords, limit)
