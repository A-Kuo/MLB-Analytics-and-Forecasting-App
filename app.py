"""Baseball Analytics Dashboard -- Streamlit entry point.

Single-page dashboard: team/season/player selection in a middle row, a
team + player header (logo/portrait), KPI cards, a regression trajectory
chart, a game log table, team-level rolling offense/defense trends, and a
toggleable news feed, all stacked on the one page.

Calls the macroservice/ package in-process (see client.py) -- no separate
server needs to be running.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

import client
from chart import build_trajectory_figure
from utils.filters import GAME_LOG_COLUMNS, metrics_for_group, stat_group_for_position
from utils.formatters import format_stat
from utils.timeline import pushed_year_control, year_range_control

st.set_page_config(page_title="Baseball Analytics Dashboard", layout="wide")

EARLIEST_SEASON = 2015
FORECAST_MAX_YEAR = 2025
DEFENSE_COLOR = "#C41E3A"

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
roster_by_name = {player["name"]: player for player in roster}
with player_col:
    player_name = st.selectbox("Player", sorted(roster_by_name), filter_mode="fuzzy") if roster_by_name else None
player = roster_by_name.get(player_name) if player_name else None

show_news = st.sidebar.toggle("News Feed", value=False)

if player is None:
    st.info("No roster available for this team/season.")
    st.stop()

group = stat_group_for_position(player["position"])

team_header_col, player_header_col = st.columns(2)
with team_header_col:
    logo_col, label_col = st.columns([1, 4])
    logo_col.image(team["logo_url"], width=72)
    label_col.markdown(f"### {team['name']}")
with player_header_col:
    portrait_col, label_col = st.columns([1, 4])
    portrait_col.image(client.get_headshot_url(player["id"]), width=72)
    label_col.markdown(f"### {player_name}")
    label_col.caption(player["position"])

with st.expander("Timeline preview (Phase 3 -- not yet wired to a graph)", expanded=True):
    st.caption(
        "Native two-handle slider + synced number inputs. Same-year overlap "
        "is allowed; the number boxes are the reliable disambiguator when "
        "both handles land on one year."
    )
    perf_start, perf_end = year_range_control("perf", EARLIEST_SEASON, current_season, label="Performance year range")

    st.caption(
        "Scrubbers 1 and 2 below mirror the range above (read-only, greyed "
        "out); scrubber 3 sets the forecast horizon and gets pushed forward "
        "if scrubber 2 moves past it, but never pushes back."
    )
    mirror_start_col, mirror_end_col = st.columns(2)
    mirror_start_col.number_input("Scrubber 1 (train start)", value=perf_start, disabled=True)
    mirror_end_col.number_input("Scrubber 2 (train end)", value=perf_end, disabled=True)
    forecast_end = pushed_year_control(
        "forecast", perf_end, FORECAST_MAX_YEAR, slider_floor_year=EARLIEST_SEASON, label="Scrubber 3 (forecast horizon)"
    )

st.subheader("Season KPIs")
season_stats = client.get_season_stats(player["id"], season, group)
kpi_defs = metrics_for_group(group)
cols = st.columns(len(kpi_defs))
for col, (key, label) in zip(cols, kpi_defs):
    col.metric(label, format_stat(season_stats.get(key), key))

st.subheader("Performance Trend")
if group == "pitching":
    trend_payload = client.get_pitcher_trajectory(player["id"], season)
    if trend_payload["x_labels"] and not trend_payload["used_statcast"]:
        st.caption(
            "Statcast pitch-level data unavailable for this pitcher/season -- "
            "showing appearance-level ERA instead."
        )
else:
    hitting_metrics = metrics_for_group("hitting")
    metric_label_by_key = dict(hitting_metrics)
    metric_key = st.selectbox(
        "Metric",
        options=[key for key, _ in hitting_metrics],
        format_func=lambda key: metric_label_by_key[key],
    )
    trend_payload = client.get_hitter_trajectory(player["id"], season, metric_key)

if trend_payload["x_labels"]:
    st.plotly_chart(build_trajectory_figure(trend_payload, team["primary_color"]), use_container_width=True)
else:
    st.info(f"No {season} game log yet for {player_name}.")

with st.expander("Game Log"):
    splits = client.get_game_log_splits(player["id"], season, group)
    if splits:
        rows = []
        for split in splits:
            row = {"date": split.get("date"), "opponent": split.get("opponent", {}).get("name", "")}
            row.update(split.get("stat", {}))
            rows.append(row)
        game_log_df = pd.DataFrame(rows)
        display_columns = [col for col in GAME_LOG_COLUMNS[group] if col in game_log_df.columns]
        st.dataframe(game_log_df[display_columns], use_container_width=True, hide_index=True)
    else:
        st.write("No games logged yet this season.")

st.subheader("Team Trends")
offense_col, defense_col = st.columns(2)
offense_payload = client.get_team_trajectory(team["id"], season, "offense")
defense_payload = client.get_team_trajectory(team["id"], season, "defense")
with offense_col:
    if offense_payload["x_labels"]:
        st.plotly_chart(build_trajectory_figure(offense_payload, team["primary_color"]), use_container_width=True)
    else:
        st.info("No completed games yet this season.")
with defense_col:
    if defense_payload["x_labels"]:
        st.plotly_chart(build_trajectory_figure(defense_payload, DEFENSE_COLOR), use_container_width=True)
    else:
        st.info("No completed games yet this season.")

if show_news:
    st.subheader("News")
    headlines = client.get_news(team["keywords"])
    if headlines:
        for headline in headlines:
            st.markdown(f"- [{headline['title']}]({headline['url']})")
    else:
        st.write("No recent headlines.")
