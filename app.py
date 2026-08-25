"""Baseball Analytics Dashboard -- Streamlit entry point.

Single-page dashboard: vertical Team -> Season -> Timeline -> Player
selection. Season filters which season's roster is browsable in the
Player multiselect; Timeline (a year-range control) is what the
Offense/Defense/All-Players bulk-selection checkboxes resolve against
(via macroservice.roster_history, an all-time-roster + date-overlap
lookup, not the single Season snapshot) -- so it has to be selected before
the Player step, not after. Selected players render as removable flags
(individually, or collapsed to one "Offense/Defense/All Players" flag when
a bulk group is fully selected -- see utils/selection_widgets.py) and as a
scrollable portrait wall below.

Calls the macroservice/ package in-process (see client.py) -- no separate
server needs to be running.

Aggregate KPI / Performance Trend / Forecast / Game Log wiring for the new
multi-player selection lands in a later phase; for now they're placeholder
text so the page stays honest about what's built vs. not.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from chart import build_trajectory_figure
import client
from macroservice.players import headshot_url
from utils.news_cards import news_card_html
from utils.selection_widgets import render_player_selection, render_portrait_wall
from utils.timeline import year_range_control

st.set_page_config(page_title="Baseball Analytics Dashboard", layout="wide")

EARLIEST_SEASON = 1901  # AL founding -- MLB Stats API's season-stats coverage goes back this far
DEFENSE_COLOR = "#C41E3A"

teams = client.get_teams()
team_by_name = {team["name"]: team for team in teams}

st.subheader("Team")
team_name = st.selectbox("Team", sorted(team_by_name), filter_mode="fuzzy", label_visibility="collapsed")
team = team_by_name[team_name]

st.subheader("Season")
current_season = pd.Timestamp.today().year
season = st.selectbox(
    "Season", list(range(EARLIEST_SEASON, current_season + 1))[::-1], label_visibility="collapsed"
)

st.subheader("Timeline")
perf_start, perf_end = year_range_control("perf", EARLIEST_SEASON, current_season, label="Season range")

st.subheader("Player")
season_roster = client.get_roster(team["id"], season)
bio_roster = client.get_team_roster_with_active_years(team["id"])
bio_by_id = {p["id"]: p for p in bio_roster}
# The season-scoped roster is what "Season selection filters the roster"
# means for browsing -- but bulk-selected ids from a wider Timeline range
# (or an earlier season) can fall outside it, so name lookups always go
# through the all-time bio_by_id map instead of this narrower one.
season_roster_ids = frozenset(p["id"] for p in season_roster)

offense_ids = frozenset(client.resolve_players_in_range(team["id"], perf_start, perf_end, "hitting"))
defense_ids = frozenset(client.resolve_players_in_range(team["id"], perf_start, perf_end, "pitching"))
all_ids = offense_ids | defense_ids

# A selection from a different team is meaningless once you switch teams.
if st.session_state.get("selected_team_id") != team["id"]:
    st.session_state["selected_team_id"] = team["id"]
    st.session_state["perf_selected_ids"] = set()

selected_ids = render_player_selection("perf", bio_by_id, offense_ids, defense_ids, all_ids)

st.caption("Selected Players")
render_portrait_wall(selected_ids, bio_by_id, headshot_url)

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

st.info(
    "Aggregate KPI, Performance Trend, Forecast, and Game Log for the new "
    "multi-player selection above are wired in a later phase of this redesign."
)

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
