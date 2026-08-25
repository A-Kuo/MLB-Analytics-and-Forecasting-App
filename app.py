"""Baseball Analytics Dashboard -- Streamlit entry point.

Single-page dashboard: team/season/player selection in a middle row (the
player selector also offers two synthetic "Offense"/"Defense" team-aggregate
entries per team, backed by MLB Stats API team-level season stats), a
team + subject header (logo/portrait), KPI cards, a year-range Performance
Trend chart (actuals only, no model fitting, updates live as metrics are
checked/unchecked), a Forecast chart (trains on the same range and projects
forward, computed only on button press), a game log table, and team-level
rolling offense/defense trends. A collapsible sidebar (freed up now that
team/player selection moved to the middle row) holds the toggleable news
feed.

Calls the macroservice/ package in-process (see client.py) -- no separate
server needs to be running.
"""
from __future__ import annotations

import time

import pandas as pd
import streamlit as st

import client
from chart import build_forecast_figure, build_multi_metric_figure, build_trajectory_figure
from macroservice.players import headshot_url
from utils.filters import (
    GAME_LOG_COLUMNS,
    full_name_for_metric,
    metrics_for_group,
    stat_group_for_position,
)
from utils.formatters import format_stat
from utils.news_cards import news_card_html
from utils.timeline import pushed_year_control, year_range_control

st.set_page_config(page_title="Baseball Analytics Dashboard", layout="wide")

EARLIEST_SEASON = 1901  # AL founding -- MLB Stats API's season-stats coverage goes back this far
FORECAST_MAX_YEAR = 2025
DEFENSE_COLOR = "#C41E3A"
REVEAL_FRAME_SECONDS = 0.06

AGGREGATE_ENTRIES = [
    {"id": None, "name": "Offense", "is_aggregate": True, "group": "hitting"},
    {"id": None, "name": "Defense", "is_aggregate": True, "group": "pitching"},
]

teams = client.get_teams()
team_by_name = {team["name"]: team for team in teams}

team_col, player_col, season_col = st.columns(3)

with team_col:
    team_name = st.selectbox("Team", sorted(team_by_name), filter_mode="fuzzy")
team = team_by_name[team_name]

current_season = pd.Timestamp.today().year
with season_col:
    # Season selection here is transitional -- the year-range timeline
    # (replacing this dropdown) lands in a later phase of the dashboard
    # redesign; downstream KPI/trend calls still need a single season
    # until then.
    season = st.selectbox("Season", list(range(EARLIEST_SEASON, current_season + 1))[::-1])

roster = client.get_roster(team["id"], season)
# "Offense"/"Defense" are always offered, even for a team/season with no
# individual roster on file -- they come from a team-level endpoint that
# doesn't depend on the roster at all.
roster_by_name = {p["name"]: p for p in AGGREGATE_ENTRIES + roster}
with player_col:
    player_name = st.selectbox("Player", sorted(roster_by_name), filter_mode="fuzzy")
player = roster_by_name[player_name]

with st.sidebar:
    show_news = st.toggle("News Feed", value=False)
    if show_news:
        st.subheader("News")
        headlines = client.get_news(team["keywords"])
        if headlines:
            with st.container(height=500):
                for headline in headlines:
                    st.markdown(
                        news_card_html(headline["title"], headline["url"], headline.get("image")),
                        unsafe_allow_html=True,
                    )
                    st.divider()
        else:
            st.write("No recent headlines.")

is_aggregate = player.get("is_aggregate", False)
group = player["group"] if is_aggregate else stat_group_for_position(player["position"])

if is_aggregate:
    subject_label = f"{team['name']} {player_name}"

    def fetch_season_stats(stats_season: int) -> dict:
        return client.get_team_season_stats(team["id"], stats_season, group)

    def fetch_season_series(metric: str, start_year: int, end_year: int) -> dict:
        return client.get_team_season_series(team["id"], metric, group, start_year, end_year)

    def fetch_metric_forecast(metric: str, train_start: int, train_end: int, forecast_end: int) -> dict:
        return client.get_team_metric_forecast(team["id"], metric, group, train_start, train_end, forecast_end)
else:
    subject_label = player_name

    def fetch_season_stats(stats_season: int) -> dict:
        return client.get_season_stats(player["id"], stats_season, group)

    def fetch_season_series(metric: str, start_year: int, end_year: int) -> dict:
        return client.get_season_series(player["id"], metric, group, start_year, end_year)

    def fetch_metric_forecast(metric: str, train_start: int, train_end: int, forecast_end: int) -> dict:
        return client.get_metric_forecast(player["id"], metric, group, train_start, train_end, forecast_end)

team_header_col, player_header_col = st.columns(2)
with team_header_col:
    logo_col, label_col = st.columns([1, 4])
    logo_col.image(team["logo_url"], width=72)
    label_col.markdown(f"### {team['name']}")
with player_header_col:
    portrait_col, label_col = st.columns([1, 4])
    if is_aggregate:
        portrait_col.image(team["logo_url"], width=72)
        label_col.markdown(f"### {player_name}")
        label_col.caption("Team Aggregate")
    else:
        portrait_col.image(headshot_url(player["id"]), width=72)
        label_col.markdown(f"### {player_name}")
        label_col.caption(player["position"])

st.subheader("Season KPIs")
season_stats = fetch_season_stats(season)
kpi_defs = metrics_for_group(group)
cols = st.columns(len(kpi_defs))
for col, (key, label) in zip(cols, kpi_defs):
    col.metric(label, format_stat(season_stats.get(key), key))

st.subheader("Performance Trend")
perf_start, perf_end = year_range_control("perf", EARLIEST_SEASON, current_season, label="Season range")

metric_panel_col, trend_graph_col = st.columns([1, 3])
with metric_panel_col:
    st.caption("Metrics")
    with st.container(height=240, border=True):
        selected_metrics = [
            (key, acronym)
            for key, acronym in metrics_for_group(group)
            if st.checkbox(full_name_for_metric(key), key=f"perf_metric_{key}")
        ]

with trend_graph_col:
    if perf_start == perf_end:
        # Both scrubbers on the same year -- a single point isn't a trend.
        st.info("Widen the season range: the two scrubbers are on the same year.")
    elif not selected_metrics:
        st.info("Select one or more metrics to visualize.")
    else:
        with st.spinner("Pulling season stats..."):
            series_by_metric = {
                key: fetch_season_series(key, perf_start, perf_end) for key, _ in selected_metrics
            }
        acronym_by_metric = dict(selected_metrics)
        populated = {key: s for key, s in series_by_metric.items() if s["years"]}

        if not populated:
            st.info(f"No {perf_start}-{perf_end} season stats for {subject_label}.")
        else:
            chart_title = f"{subject_label} — {perf_start} to {perf_end}"
            # Re-animate the snake reveal whenever the subject or the set of
            # displayed metrics changes -- not on every rerun (e.g. dragging
            # a scrubber shouldn't replay the animation for an unchanged set).
            display_key = (team["id"], player["id"], frozenset(populated))
            should_animate = st.session_state.get("perf_last_shown_key") != display_key
            st.session_state["perf_last_shown_key"] = display_key

            slot = st.empty()
            if should_animate:
                frames = max(len(s["years"]) for s in populated.values())
                for reveal in range(1, frames):
                    slot.plotly_chart(
                        build_multi_metric_figure(populated, acronym_by_metric, reveal, chart_title)
                    )
                    time.sleep(REVEAL_FRAME_SECONDS)
            slot.plotly_chart(build_multi_metric_figure(populated, acronym_by_metric, None, chart_title))

st.subheader("Forecast")
st.caption(
    "Scrubbers 1 and 2 mirror the season range above (read-only) and mark "
    "the training window; drag scrubber 3 to set how far out to forecast."
)
mirror_start_col, mirror_end_col = st.columns(2)
mirror_start_col.number_input("Scrubber 1 (train start)", value=perf_start, disabled=True, key="forecast_mirror_start")
mirror_end_col.number_input("Scrubber 2 (train end)", value=perf_end, disabled=True, key="forecast_mirror_end")
forecast_end = pushed_year_control(
    "forecast", perf_end, FORECAST_MAX_YEAR, slider_floor_year=EARLIEST_SEASON, label="Scrubber 3 (forecast horizon)"
)

# The last-computed forecast is cached per subject, so switching player/team
# doesn't show a stale forecast for the wrong subject until Forecast is
# pressed again.
forecast_subject_key = (team["id"], player["id"], group)
if st.session_state.get("forecast_subject") != forecast_subject_key:
    st.session_state["forecast_subject"] = forecast_subject_key
    st.session_state["forecast_computed"] = {}
    st.session_state["forecast_acronyms"] = {}

forecast_metric_panel_col, forecast_graph_col = st.columns([1, 3])
with forecast_metric_panel_col:
    st.caption("Metrics")
    with st.container(height=240, border=True):
        forecast_selected_metrics = [
            (key, acronym)
            for key, acronym in metrics_for_group(group)
            if st.checkbox(full_name_for_metric(key), key=f"forecast_metric_{key}")
        ]
    forecast_pressed = st.button("Forecast", type="primary")

with forecast_graph_col:
    current_forecast_keys = {key for key, _ in forecast_selected_metrics}
    computed = st.session_state.get("forecast_computed", {})

    if forecast_pressed and forecast_end > perf_end and forecast_selected_metrics:
        # Forecasting fits a real model per metric -- this is the only path
        # that ever does that work; every other branch below just filters
        # or clears the last computed result.
        with st.spinner("Fitting forecast..."):
            computed = {
                key: fetch_metric_forecast(key, perf_start, perf_end, forecast_end)
                for key, _ in forecast_selected_metrics
            }
        st.session_state["forecast_computed"] = computed
        st.session_state["forecast_acronyms"] = dict(forecast_selected_metrics)
        st.session_state["forecast_animate"] = True
    elif current_forecast_keys - computed.keys():
        # A checked metric was never part of the last computed forecast
        # (newly checked, or Forecast was pressed while in an invalid
        # state and nothing new was computed) -- clear until Forecast is
        # pressed again, rather than silently forecasting on a partial or
        # stale set.
        computed = {}
        st.session_state["forecast_computed"] = {}

    # Unchecked metrics are simply filtered out here -- no recompute, no
    # clearing, they just drop off the graph immediately.
    display_metrics = {key: computed[key] for key in current_forecast_keys if key in computed}
    forecast_acronym_by_metric = st.session_state.get("forecast_acronyms", {})

    if forecast_end <= perf_end:
        # Scrubber 3 at or before scrubber 2 -- a zero-or-negative-width
        # forecast window. Not just ==: forecast_end is clamped to
        # FORECAST_MAX_YEAR, so it can end up *before* perf_end whenever
        # perf_end itself exceeds that fixed ceiling (e.g. perf_end is the
        # current year and that's later than FORECAST_MAX_YEAR).
        st.info("Widen the forecast horizon: scrubber 3 is at or before scrubber 2.")
    elif not forecast_selected_metrics:
        st.info("Select one or more metrics, then press Forecast.")
    elif not display_metrics:
        st.info("Press Forecast to compute the checked metrics.")
    else:
        forecast_populated = {key: p for key, p in display_metrics.items() if p["years"]}

        if not forecast_populated:
            st.info(f"No training data in {perf_start}-{perf_end} for {subject_label}.")
        else:
            forecast_title = f"{subject_label} — forecast {perf_end} to {forecast_end}"
            forecast_slot = st.empty()
            if st.session_state.get("forecast_animate"):
                frames = max(len(p["years"]) for p in forecast_populated.values())
                for reveal in range(1, frames):
                    forecast_slot.plotly_chart(
                        build_forecast_figure(forecast_populated, forecast_acronym_by_metric, reveal, forecast_title)
                    )
                    time.sleep(REVEAL_FRAME_SECONDS)
                st.session_state["forecast_animate"] = False
            forecast_slot.plotly_chart(
                build_forecast_figure(forecast_populated, forecast_acronym_by_metric, None, forecast_title)
            )

with st.expander("Game Log"):
    if is_aggregate:
        st.info(
            "Game log isn't available for team aggregates -- see Team Trends "
            "below for game-by-game rolling trends."
        )
    else:
        splits = client.get_game_log_splits(player["id"], season, group)
        if splits:
            rows = []
            for split in splits:
                row = {"date": split.get("date"), "opponent": split.get("opponent", {}).get("name", "")}
                row.update(split.get("stat", {}))
                rows.append(row)
            game_log_df = pd.DataFrame(rows)
            display_columns = [col for col in GAME_LOG_COLUMNS[group] if col in game_log_df.columns]
            st.dataframe(game_log_df[display_columns], hide_index=True)
        else:
            st.write("No games logged yet this season.")

st.subheader("Team Trends")
offense_col, defense_col = st.columns(2)
offense_payload = client.get_team_trajectory(team["id"], season, "offense")
defense_payload = client.get_team_trajectory(team["id"], season, "defense")
with offense_col:
    if offense_payload["x_labels"]:
        st.plotly_chart(build_trajectory_figure(offense_payload, team["primary_color"]))
    else:
        st.info("No completed games yet this season.")
with defense_col:
    if defense_payload["x_labels"]:
        st.plotly_chart(build_trajectory_figure(defense_payload, DEFENSE_COLOR))
    else:
        st.info("No completed games yet this season.")
