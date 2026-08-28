"""Insights -- season leaderboards by metric, sourced entirely from
Postgres (no live-API fallback; see client.get_insights_leaderboard).

A team selector (all 30 teams, defaulting to all selected) scopes every
leaderboard below it to a chosen set of teams; a season picker scopes them
to one season. Each of the ~22 hitting/pitching/Statcast metrics in
utils/filters.py gets its own collapsible leaderboard showing the top 10
players for that metric/season among the selected teams.

Coverage depends on scripts/backfill_season_leaderboard.py having been run
for the chosen season -- the season-stats cache elsewhere in this app is
lazy (populated only for players someone has looked up), which isn't
enough for a "top 10" leaderboard to mean anything. An empty leaderboard
names the exact backfill command to run.
"""
from __future__ import annotations

import datetime

import streamlit as st

import client
from macroservice.players import headshot_url
from macroservice.roster_history import active_years_label
from utils.constants import EARLIEST_SEASON
from utils.filters import HITTING_METRICS, PITCHING_METRICS, full_name_for_metric
from utils.formatters import format_stat
from utils.selection_widgets import sync_bulk_checkbox
from utils.team_cards import team_flag_html, team_flag_wall_html

LEADERBOARD_LIMIT = 10
TEAMS_PER_ROW = 6

st.subheader("Teams")

teams = client.get_teams()
team_by_id = {team["id"]: team for team in teams}
all_team_ids = frozenset(team_by_id)

ids_key = "insights_selected_team_ids"
if ids_key not in st.session_state:
    st.session_state[ids_key] = set(all_team_ids)
selected = st.session_state[ids_key]

# 1. Plain grid of individual team checkboxes, alphabetical -- deliberately
# not grouped by division here, since the bulk-select row below already
# provides that grouping; doing both would just duplicate the structure.
ordered_teams = sorted(teams, key=lambda t: t["name"])
for row_start in range(0, len(ordered_teams), TEAMS_PER_ROW):
    row_teams = ordered_teams[row_start : row_start + TEAMS_PER_ROW]
    cols = st.columns(TEAMS_PER_ROW)
    for col, team in zip(cols, row_teams):
        team_key = f"insights_team_cb_{team['id']}"
        st.session_state[team_key] = team["id"] in selected
        col.checkbox(
            team["abbreviation"],
            key=team_key,
            on_change=sync_bulk_checkbox,
            args=(team_key, ids_key, frozenset({team["id"]})),
        )

# 2. Scrollable flag window -- a real, distinct colored badge per selected
# team (unlike the player selector's multiselect-only pills), reusing
# team["primary_color"].
current = st.session_state[ids_key]
st.caption("Selected Teams")
with st.container(height=140, border=True):
    cards = [team_flag_html(team_by_id[tid]) for tid in sorted(current, key=lambda tid: team_by_id[tid]["name"])]
    st.markdown(team_flag_wall_html(cards), unsafe_allow_html=True)

# 3. Bulk-select: an "All Teams" master checkbox, then American/National
# League rows each paired with East/Central/West division checkboxes.
current = st.session_state[ids_key]
all_key = "insights_all_teams_cb"
st.session_state[all_key] = current >= all_team_ids
st.checkbox("All Teams", key=all_key, on_change=sync_bulk_checkbox, args=(all_key, ids_key, all_team_ids))

for league, league_label in (("AL", "American League"), ("NL", "National League")):
    league_ids = frozenset(t["id"] for t in teams if t["league"] == league)
    cols = st.columns([2, 1, 1, 1])
    league_key = f"insights_league_{league}_cb"
    st.session_state[league_key] = bool(league_ids) and current >= league_ids
    cols[0].checkbox(
        league_label, key=league_key, on_change=sync_bulk_checkbox, args=(league_key, ids_key, league_ids)
    )
    for col, division in zip(cols[1:], ("East", "Central", "West")):
        division_ids = frozenset(t["id"] for t in teams if t["league"] == league and t["division"] == division)
        division_key = f"insights_div_{league}_{division}_cb"
        st.session_state[division_key] = bool(division_ids) and current >= division_ids
        col.checkbox(
            division, key=division_key, on_change=sync_bulk_checkbox, args=(division_key, ids_key, division_ids)
        )

selected_team_ids = frozenset(st.session_state[ids_key])

# News Feed itself is rendered once, shared across both pages, by app.py
# (the router) after this page's script finishes running -- see app.py's
# comment on why. This page only hands off which teams are selected; the
# shared renderer owns the per-team cap and hub-link derivation, since it
# can get everything it needs from team_ids alone via macroservice.teams.
st.session_state["news_context"] = {"team_ids": selected_team_ids}

st.subheader("Season")
current_year = datetime.datetime.now().year
season_options = list(range(current_year, EARLIEST_SEASON - 1, -1))
season = st.selectbox("Season", season_options, index=season_options.index(current_year - 1))

st.divider()
st.subheader("Leaderboards")

_leaderboard_error_slot = st.empty()
_db_state = {"error_shown": False}


def _leaderboard_rows(key: str, group: str) -> list[dict] | None:
    """None on a DB-connectivity failure (already reported once via the
    page-level banner above -- not per-expander); [] on a genuine
    no-data-yet cache miss.
    """
    try:
        return client.get_insights_leaderboard(key, group, season, selected_team_ids, LEADERBOARD_LIMIT)
    except Exception:
        if not _db_state["error_shown"]:
            _leaderboard_error_slot.error(
                "Couldn't reach the leaderboard database. Configure Postgres in "
                "`.streamlit/secrets.toml` (see macroservice/db.py) to use Insights."
            )
            _db_state["error_shown"] = True
        return None


def _render_leaderboard(key: str, acronym: str, group: str) -> None:
    with st.expander(f"{full_name_for_metric(key)} ({acronym})"):
        if not selected_team_ids:
            st.info("Select at least one team.")
            return

        rows = _leaderboard_rows(key, group)
        if rows is None:
            return
        if not rows:
            st.info(
                f"No cached data for {season} among the selected teams yet. Run:\n\n"
                f"`python scripts/backfill_season_leaderboard.py --season {season}`"
            )
            return

        for rank, row in enumerate(rows, start=1):
            rank_col, portrait_col, name_col, value_col = st.columns([1, 2, 5, 3])
            rank_col.write(f"#{rank}")
            portrait_col.image(headshot_url(row["player_id"]), width=60)
            years = active_years_label(row["debut_year"], row["last_active_year"], row["active"])
            name_col.write(f"{row['name']} ({years})" if years else row["name"])
            value_col.write(format_stat(row["metric_value"], key))


st.markdown("#### Hitting")
for metric_key, metric_acronym in HITTING_METRICS:
    _render_leaderboard(metric_key, metric_acronym, "hitting")

st.markdown("#### Pitching")
for metric_key, metric_acronym in PITCHING_METRICS:
    _render_leaderboard(metric_key, metric_acronym, "pitching")
