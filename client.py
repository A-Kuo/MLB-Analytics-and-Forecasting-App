"""Streamlit-facing facade over the macroservice's domain modules.

Calls macroservice functions directly, in-process -- no HTTP hop. Each
function keeps its own @st.cache_data layer on top of the macroservice's
internal TTLCache (macroservice.caching): the two serve different purposes
(st.cache_data is Streamlit's rerun-aware cache; the macroservice's TTLCache
still applies when macroservice.api is run standalone, without Streamlit in
front of it), so both are intentional, not redundant.
"""
from __future__ import annotations

import datetime
import logging

import streamlit as st

from macroservice import news, players, roster_history, roster_history_db, season_stats_db, statcast_season, teams, trajectories
from utils.aggregation import aggregate_scalar, aggregate_series
from utils.filters import STATCAST_METRIC_KEYS, is_rate_metric

logger = logging.getLogger(__name__)


def _is_season_complete(season: int) -> bool:
    """A season is only cacheable once it can never change again.

    The current, in-progress season's stats/game-logs update after every
    game, so caching them "forever" on first read would go stale --
    ``season < this year`` is safe by definition once the calendar rolls
    over. The ~2-month window each Nov-Dec where a just-finished season
    could theoretically be cached slightly earlier is an accepted,
    self-correcting conservatism, not a bug.
    """
    return season < datetime.datetime.now().year


@st.cache_data(ttl=3600)
def get_teams() -> list[dict]:
    return teams.TEAMS


@st.cache_data(ttl=3600)
def get_roster(team_id: int, season: int) -> list[dict]:
    return teams.get_roster(team_id, season)


def _db_engine():
    """SQLAlchemy engine shared by every Postgres-backed cache (roster
    history, season stats). st.connection caches the connection object
    itself across reruns (keyed by name), so this needs no cache decorator
    of its own.

    Raises when no [connections.postgresql] secret is configured -- callers
    must treat that as "cache unavailable", not a fatal error, so the app
    still runs before anyone wires up secrets.
    """
    return st.connection("postgresql", type="sql").engine


@st.cache_data(ttl=3600)
def get_team_roster_with_active_years(team_id: int) -> list[dict]:
    """Postgres-first, with a live-API fallback that self-heals the cache.

    A team missing from Postgres (backfill hasn't covered it yet) is a
    cache miss, not an error: fetch live, then write it back so the next
    read is fast. Every DB interaction -- including opening the connection
    -- is guarded, because degrading to the pre-migration live-API behavior
    beats breaking the dashboard when secrets aren't configured or Neon has
    a blip. The tradeoff is that a sustained outage shows up only in logs.
    """
    try:
        engine = _db_engine()
        rows = roster_history_db.fetch_team_roster_rows(engine, team_id)
    except Exception:
        logger.warning("Roster cache read failed for team %s; falling back to live API", team_id, exc_info=True)
        engine = None
        rows = []

    if rows:
        return roster_history.enrich_with_active_years(rows)

    roster = roster_history.get_team_roster_with_active_years(team_id)
    if engine is not None:
        try:
            roster_history_db.upsert_team_roster(engine, team_id, roster)
        except Exception:
            logger.warning("Roster cache write failed for team %s; serving live data", team_id, exc_info=True)
    return roster


@st.cache_data(ttl=3600)
def resolve_players_in_range(
    team_id: int, start_year: int, end_year: int, positions: frozenset[str] | None = None
) -> set[int]:
    # Deliberately goes through this module's DB-backed roster fetch above
    # rather than roster_history.resolve_players_in_range, so all 14
    # per-position calls in one render share a single cached roster.
    roster = get_team_roster_with_active_years(team_id)
    return roster_history.resolve_from_roster(roster, start_year, end_year, positions)


@st.cache_data(ttl=60)
def get_season_stats(player_id: int, season: int, group: str) -> dict:
    """Postgres-first once ``season`` is complete, with a live-API fallback
    that self-heals the cache -- same shape as get_team_roster_with_active_years.
    The current season always bypasses Postgres entirely (see
    _is_season_complete): season stats change after every game, so caching
    an in-progress season would go stale.
    """
    if not _is_season_complete(season):
        return players.get_season_stats(player_id, season, group)

    fetch = season_stats_db.fetch_player_season_hitting if group == "hitting" else season_stats_db.fetch_player_season_pitching
    upsert = season_stats_db.upsert_player_season_hitting if group == "hitting" else season_stats_db.upsert_player_season_pitching

    try:
        engine = _db_engine()
        cached = fetch(engine, player_id, season)
    except Exception:
        logger.warning("Season-stats cache read failed for player %s/%s; falling back to live API", player_id, season, exc_info=True)
        engine = None
        cached = None

    if cached is not None:
        return cached

    stats = players.get_season_stats(player_id, season, group)
    if engine is not None:
        try:
            upsert(engine, player_id, season, stats)
        except Exception:
            logger.warning("Season-stats cache write failed for player %s/%s; serving live data", player_id, season, exc_info=True)
    return stats


@st.cache_data(ttl=60)
def get_team_season_stats(team_id: int, season: int, group: str) -> dict:
    """Same Postgres-first/live-API-fallback shape as get_season_stats,
    for the team-level analogue.
    """
    if not _is_season_complete(season):
        return teams.get_team_season_stats(team_id, season, group)

    fetch = season_stats_db.fetch_team_season_hitting if group == "hitting" else season_stats_db.fetch_team_season_pitching
    upsert = season_stats_db.upsert_team_season_hitting if group == "hitting" else season_stats_db.upsert_team_season_pitching

    try:
        engine = _db_engine()
        cached = fetch(engine, team_id, season)
    except Exception:
        logger.warning("Team season-stats cache read failed for team %s/%s; falling back to live API", team_id, season, exc_info=True)
        engine = None
        cached = None

    if cached is not None:
        return cached

    stats = teams.get_team_season_stats(team_id, season, group)
    if engine is not None:
        try:
            upsert(engine, team_id, season, stats)
        except Exception:
            logger.warning("Team season-stats cache write failed for team %s/%s; serving live data", team_id, season, exc_info=True)
    return stats


@st.cache_data(ttl=60)
def get_game_log_splits(player_id: int, season: int, group: str) -> list[dict]:
    """Same Postgres-first/live-API-fallback shape as get_season_stats.

    A cache hit of ``[]`` is ambiguous with "not cached yet" (see
    season_stats_db's module docstring) -- worst case a genuinely gameless
    season gets re-fetched from the live API every time, which is harmless.
    """
    if not _is_season_complete(season):
        return players.get_game_log(player_id, season, group)

    fetch = season_stats_db.fetch_player_game_log_hitting if group == "hitting" else season_stats_db.fetch_player_game_log_pitching
    upsert = season_stats_db.upsert_player_game_log_hitting if group == "hitting" else season_stats_db.upsert_player_game_log_pitching

    try:
        engine = _db_engine()
        cached = fetch(engine, player_id, season)
    except Exception:
        logger.warning("Game-log cache read failed for player %s/%s; falling back to live API", player_id, season, exc_info=True)
        engine = None
        cached = []

    if cached:
        return cached

    splits = players.get_game_log(player_id, season, group)
    if engine is not None:
        try:
            upsert(engine, player_id, season, splits)
        except Exception:
            logger.warning("Game-log cache write failed for player %s/%s; serving live data", player_id, season, exc_info=True)
    return splits


def _get_statcast_season(player_id: int, season: int, group: str) -> dict:
    """Postgres-first/live-API-fallback for one player-season's Statcast
    aggregate -- the cached building block get_unified_series' Statcast
    branch loops per year, instead of looping the uncached
    statcast_season.compute_*_statcast_season directly. No @st.cache_data
    of its own: get_unified_series (its only caller) already carries one.
    """
    if not _is_season_complete(season):
        if group == "pitching":
            return statcast_season.compute_pitcher_statcast_season(player_id, season)
        return statcast_season.compute_hitter_statcast_season(player_id, season)

    fetch = season_stats_db.fetch_player_statcast_pitching_season if group == "pitching" else season_stats_db.fetch_player_statcast_hitting_season
    upsert = season_stats_db.upsert_player_statcast_pitching_season if group == "pitching" else season_stats_db.upsert_player_statcast_hitting_season
    compute = statcast_season.compute_pitcher_statcast_season if group == "pitching" else statcast_season.compute_hitter_statcast_season

    try:
        engine = _db_engine()
        cached = fetch(engine, player_id, season)
    except Exception:
        logger.warning("Statcast-season cache read failed for player %s/%s; falling back to live API", player_id, season, exc_info=True)
        engine = None
        cached = None

    if cached is not None:
        return cached

    stats = compute(player_id, season)
    if engine is not None:
        try:
            upsert(engine, player_id, season, stats)
        except Exception:
            logger.warning("Statcast-season cache write failed for player %s/%s; serving live data", player_id, season, exc_info=True)
    return stats


@st.cache_data(ttl=60)
def get_season_series(player_id: int, metric: str, group: str, start_year: int, end_year: int) -> dict:
    """Loops this module's cached get_season_stats per year -- not
    players.get_season_series, which loops the *uncached*
    players.get_season_stats and would bypass the Postgres cache entirely.
    """
    years: list[int] = []
    values: list[float] = []
    for year in range(start_year, end_year + 1):
        stat = get_season_stats(player_id, year, group).get(metric)
        if stat is None:
            continue
        try:
            values.append(float(stat))
        except (TypeError, ValueError):
            continue
        years.append(year)
    return {"years": years, "values": values}


@st.cache_data(ttl=60)
def get_team_season_series(team_id: int, metric: str, group: str, start_year: int, end_year: int) -> dict:
    """Loops this module's cached get_team_season_stats per year -- see
    get_season_series' docstring for why this doesn't delegate to
    teams.get_team_season_series.
    """
    years: list[int] = []
    values: list[float] = []
    for year in range(start_year, end_year + 1):
        stat = get_team_season_stats(team_id, year, group).get(metric)
        if stat is None:
            continue
        try:
            values.append(float(stat))
        except (TypeError, ValueError):
            continue
        years.append(year)
    return {"years": years, "values": values}


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

    Loops _get_statcast_season (Postgres-first, per-season) rather than
    statcast_season.get_hitter_statcast_series/get_pitcher_statcast_series
    directly -- those loop the *uncached* compute function per year, which
    would skip the season-stats cache entirely.
    """
    if metric in STATCAST_METRIC_KEYS:
        years: list[int] = []
        values: list[float] = []
        for year in range(max(start_year, statcast_season.STATCAST_ERA_START_YEAR), end_year + 1):
            value = _get_statcast_season(player_id, year, group).get(metric)
            if value is None:
                continue
            years.append(year)
            values.append(value)
        return {"years": years, "values": values}
    return get_season_series(player_id, metric, group, start_year, end_year)


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
