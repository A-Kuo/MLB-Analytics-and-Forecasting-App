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

from macroservice import news, players, roster_history, statcast_season, teams, trajectories
from utils.aggregation import aggregate_scalar, aggregate_series
from utils.filters import STATCAST_METRIC_KEYS, is_rate_metric


@st.cache_data(ttl=3600)
def get_teams() -> list[dict]:
    return teams.TEAMS


@st.cache_data(ttl=3600)
def get_roster(team_id: int, season: int) -> list[dict]:
    return teams.get_roster(team_id, season)


@st.cache_data(ttl=3600)
def get_team_roster_with_active_years(team_id: int) -> list[dict]:
    return roster_history.get_team_roster_with_active_years(team_id)


@st.cache_data(ttl=3600)
def resolve_players_in_range(team_id: int, start_year: int, end_year: int, group: str | None = None) -> set[int]:
    return roster_history.resolve_players_in_range(team_id, start_year, end_year, group)


@st.cache_data(ttl=60)
def get_season_stats(player_id: int, season: int, group: str) -> dict:
    return players.get_season_stats(player_id, season, group)


@st.cache_data(ttl=60)
def get_team_season_stats(team_id: int, season: int, group: str) -> dict:
    return teams.get_team_season_stats(team_id, season, group)


@st.cache_data(ttl=60)
def get_game_log_splits(player_id: int, season: int, group: str) -> list[dict]:
    return players.get_game_log(player_id, season, group)


@st.cache_data(ttl=60)
def get_season_series(player_id: int, metric: str, group: str, start_year: int, end_year: int) -> dict:
    return players.get_season_series(player_id, metric, group, start_year, end_year)


@st.cache_data(ttl=60)
def get_team_season_series(team_id: int, metric: str, group: str, start_year: int, end_year: int) -> dict:
    return teams.get_team_season_series(team_id, metric, group, start_year, end_year)


@st.cache_data(ttl=60)
def get_unified_series(player_id: int, metric: str, group: str, start_year: int, end_year: int) -> dict:
    """Routes to the Statcast-backed series (macroservice.statcast_season)
    when ``metric`` is a Statcast-derived key, else the plain MLB Stats API
    series (players.get_season_series) -- callers never need to know which
    backend a given metric key came from. Player-scoped only: aggregating
    Statcast metrics across a team/multi-player selection happens by
    combining several calls to this function, one per player, at the
    call-site aggregation layer -- there's no separate team-level Statcast
    fetch, since every Statcast metric is a rate stat and the aggregation
    rule is already "mean of each selected player's own value."
    """
    if metric in STATCAST_METRIC_KEYS:
        if group == "pitching":
            return statcast_season.get_pitcher_statcast_series(player_id, metric, start_year, end_year)
        return statcast_season.get_hitter_statcast_series(player_id, metric, start_year, end_year)
    return players.get_season_series(player_id, metric, group, start_year, end_year)


@st.cache_data(ttl=60)
def get_aggregate_kpi(player_ids: tuple[int, ...], metric: str, group: str, start_year: int, end_year: int) -> float | None:
    """One number per metric, combining every selected player's own season
    series over [start_year, end_year] -- sum for counting stats, mean for
    rate stats (utils.aggregation), the same rule whether 1 player, many,
    or an entire team roster is selected.
    """
    series_by_player = {pid: get_unified_series(pid, metric, group, start_year, end_year) for pid in player_ids}
    return aggregate_scalar(series_by_player, is_rate_metric(metric))


@st.cache_data(ttl=60)
def get_aggregate_series(player_ids: tuple[int, ...], metric: str, group: str, start_year: int, end_year: int) -> dict:
    """The multi-player analogue of get_season_series/get_team_season_series
    -- one combined {"years", "values"} series across every selected
    player, for the Performance Trend chart.
    """
    series_by_player = {pid: get_unified_series(pid, metric, group, start_year, end_year) for pid in player_ids}
    return aggregate_series(series_by_player, is_rate_metric(metric))


@st.cache_data(ttl=300)
def get_aggregate_forecast(
    player_ids: tuple[int, ...], metric: str, group: str, train_start: int, train_end: int, forecast_end: int
) -> dict:
    """The multi-player analogue of get_metric_forecast/get_team_metric_forecast
    -- fits the same forecast ensemble on the combined series across every
    selected player, reusing trajectories.compute_forecast_from_series
    (already parameterized over "how do I get the series" for exactly
    this reason).
    """
    is_rate = is_rate_metric(metric)

    def get_series(series_metric: str, series_group: str, start_year: int, end_year: int) -> dict:
        series_by_player = {
            pid: get_unified_series(pid, series_metric, series_group, start_year, end_year) for pid in player_ids
        }
        return aggregate_series(series_by_player, is_rate)

    return trajectories.compute_forecast_from_series(get_series, metric, group, train_start, train_end, forecast_end)


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
def get_metric_forecast(player_id: int, metric: str, group: str, train_start: int, train_end: int, forecast_end: int) -> dict:
    return trajectories.compute_metric_forecast(player_id, metric, group, train_start, train_end, forecast_end)


@st.cache_data(ttl=300)
def get_team_metric_forecast(team_id: int, metric: str, group: str, train_start: int, train_end: int, forecast_end: int) -> dict:
    return trajectories.compute_team_metric_forecast(team_id, metric, group, train_start, train_end, forecast_end)


@st.cache_data(ttl=300)
def get_news(keywords: list[str], limit: int = 10, days: int = news.DEFAULT_LOOKBACK_DAYS) -> list[dict]:
    return news.get_headlines(keywords, limit, days)
