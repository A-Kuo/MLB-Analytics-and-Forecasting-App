"""Baseball Analytics Dashboard -- Streamlit entry point.

Two dashboard panels sit permanently side by side (st.columns(2)) for
side-by-side comparison -- not a sliding/toggled second page. Panel A keeps
today's eager first-team default; Panel B starts genuinely empty (no team
picked) and shows only a prompt until one is chosen. Both panels are the
same render_dashboard_panel(...) call, just with different defaults and
key_prefix-namespaced session state (see the k() helper) so neither panel's
widgets collide with the other's.

Within a panel: vertical Team -> Season -> Timeline -> Player selection.
Season filters which season's roster is browsable in the Player
multiselect; Timeline (a year-range control) is what the Offense/Defense/
All-Players bulk-selection checkboxes resolve against (via
macroservice.roster_history, an all-time-roster + date-overlap lookup, not
the single Season snapshot) -- so it has to be selected before the Player
step, not after. Selected players render as removable flags (individually,
or collapsed to one "Offense/Defense/All Players" flag when a bulk group is
fully selected -- see utils/selection_widgets.py) and as a scrollable
portrait wall below.

Calls the macroservice/ package in-process (see client.py) -- no separate
server needs to be running.

Aggregate KPI, Performance Trend, and Forecast all combine every currently
selected player's own data (sum for counting stats, mean for rate stats --
see utils/aggregation.py) over the Timeline's year range, regardless of
whether that's one player, a manual handful, or an entire bulk-selected
group. Since hitting and pitching metrics can't be meaningfully combined,
those three sections show one stat group at a time -- whichever type has
more players in the current selection (utils.player_selection.group_for_selection).

Team Trends (the old per-game rolling trajectory section) is commented out
below rather than deleted -- it was built for a single team and needs a
multi-player-aware redesign before it fits this panel model. See the
"Team Trends redesign notes" section of the approved plan
(synthetic-roaming-lagoon.md) for the two redesign directions considered.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import pandas as pd
import streamlit as st

from chart import build_forecast_figure, build_multi_metric_figure  # build_trajectory_figure: see Team Trends below
import client
from macroservice.players import headshot_url
from utils.filters import GAME_LOG_COLUMNS, full_name_for_metric, metrics_for_group
from utils.formatters import format_stat
from utils.metric_selection import metric_button_state_machine, reset_on_subject_change
from utils.news_cards import news_card_html
from utils.player_selection import group_for_selection
from utils.selection_widgets import render_player_selection, render_portrait_wall
from utils.timeline import pushed_year_control, year_range_control

st.set_page_config(page_title="Baseball Analytics Dashboard", layout="wide")

EARLIEST_SEASON = 1901  # AL founding -- MLB Stats API's season-stats coverage goes back this far
FORECAST_MAX_YEAR = 2025
DEFENSE_COLOR = "#C41E3A"
REVEAL_FRAME_SECONDS = 0.06


def k(prefix: str, name: str) -> str:
    """Namespaces a literal session-state/widget key by panel prefix, so
    the two side-by-side panels (see render_dashboard_panel) never collide.
    """
    return f"{prefix}_{name}"


@dataclass
class PanelSelection:
    """What one panel resolved to, for the shared news sidebar (Phase 7:
    a merged feed keyed on both panels' teams and selected player names)
    to consume without reaching back into this function's internals.
    """

    team: dict | None
    selected_ids: frozenset[int] = field(default_factory=frozenset)
    bio_by_id: dict = field(default_factory=dict)


def render_dashboard_panel(
    key_prefix: str,
    team_by_name: dict,
    default_team_name: str | None,
    narrow: bool = False,
) -> PanelSelection:
    """Renders one full Team -> Season -> Timeline -> Player -> Aggregate
    KPI -> Performance Trend -> Forecast -> Game Log dashboard panel.

    ``default_team_name`` set to a real name eagerly selects that team
    (Panel A's behavior, unchanged from before this became two panels);
    ``None`` starts the panel genuinely empty -- team and everything below
    it stay unrendered until one is picked (Panel B), per the "compromise"
    of a permanent second panel rather than a sliding/toggled one.

    ``narrow`` swaps the metrics-panel/graph [1, 3]-style column splits for
    a stacked layout, since a half-width column makes a 1-part-of-4 sliver
    too thin to hold a checkbox list.
    """
    st.subheader("Team")
    team_logo_col, team_select_col = st.columns([1, 8])
    team_options = sorted(team_by_name)
    team_index = team_options.index(default_team_name) if default_team_name is not None else None
    team_name = team_select_col.selectbox(
        "Team",
        team_options,
        index=team_index,
        placeholder="Choose a team to compare",
        filter_mode="fuzzy",
        label_visibility="collapsed",
        key=k(key_prefix, "team_select"),
    )
    if team_name is None:
        st.info("Select a team to add a comparison panel.")
        return PanelSelection(team=None)

    team = team_by_name[team_name]
    # st.selectbox renders plain text per option -- Streamlit's native widget
    # has no way to embed an image inside the dropdown list itself, so the
    # selected team's logo is shown here instead, next to the selector.
    team_logo_col.image(team["logo_url"], width=56)

    st.subheader("Season")
    current_season = pd.Timestamp.today().year
    season = st.selectbox(
        "Season",
        list(range(EARLIEST_SEASON, current_season + 1))[::-1],
        label_visibility="collapsed",
        key=k(key_prefix, "season_select"),
    )

    st.subheader("Timeline")
    perf_start, perf_end = year_range_control(
        k(key_prefix, "perf"), EARLIEST_SEASON, current_season, label="Season range"
    )

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
    if st.session_state.get(k(key_prefix, "selected_team_id")) != team["id"]:
        st.session_state[k(key_prefix, "selected_team_id")] = team["id"]
        st.session_state[k(key_prefix, "perf_selected_ids")] = set()

    selected_ids = render_player_selection(
        k(key_prefix, "perf"), bio_by_id, offense_ids, defense_ids, all_ids, season_roster_ids
    )

    st.caption("Selected Players")
    render_portrait_wall(selected_ids, bio_by_id, headshot_url)

    selected_group = group_for_selection(frozenset(selected_ids), bio_by_id)
    selected_tuple = tuple(sorted(selected_ids))
    pitcher_count = sum(1 for pid in selected_ids if bio_by_id.get(pid, {}).get("is_pitcher", False))
    hitter_count = len(selected_ids) - pitcher_count

    if pitcher_count and hitter_count:
        excluded_count = hitter_count if selected_group == "pitching" else pitcher_count
        excluded_kind = "hitter" if selected_group == "pitching" else "pitcher"
        st.caption(
            f"Showing {selected_group} metrics ({'pitchers' if selected_group == 'pitching' else 'hitters'} "
            f"make up more of your selection) -- {excluded_count} {excluded_kind}"
            f"{'s' if excluded_count != 1 else ''} excluded, since hitting and pitching stats "
            "can't be meaningfully combined."
        )

    st.subheader("Aggregate KPI")
    # Button-gated: KPI has no per-metric checkboxes (every metric for the
    # current group is always shown together), so it only needs the
    # subject-change half of the shared state machine -- switching team/players/
    # group/timeline invalidates the last Calculate press rather than silently
    # showing KPIs for a different subject.
    kpi_subject_key = (team["id"], frozenset(selected_ids), selected_group, perf_start, perf_end)
    reset_on_subject_change(k(key_prefix, "kpi_subject"), kpi_subject_key, {k(key_prefix, "kpi_values"): None})

    kpi_pressed = st.button(
        "Calculate", key=k(key_prefix, "kpi_calculate_btn"), type="primary", disabled=not selected_ids
    )
    if kpi_pressed:
        with st.spinner("Calculating aggregate KPIs..."):
            st.session_state[k(key_prefix, "kpi_values")] = {
                key: client.get_aggregate_kpi(selected_tuple, key, selected_group, perf_start, perf_end)
                for key, _ in metrics_for_group(selected_group)
            }

    kpi_values = st.session_state.get(k(key_prefix, "kpi_values"))
    if not selected_ids:
        st.info("Select one or more players, then press Calculate.")
    elif kpi_values is None:
        st.info("Press Calculate to compute aggregate KPIs for the current selection.")
    else:
        kpi_defs = metrics_for_group(selected_group)
        kpi_cols = st.columns(len(kpi_defs))
        for col, (key, acronym) in zip(kpi_cols, kpi_defs):
            col.metric(f"{full_name_for_metric(key)} ({acronym})", format_stat(kpi_values.get(key), key))

    st.subheader("Performance Trend")
    # Subject key deliberately mirrors Forecast's below (team + selected players
    # + group only, not the timeline range) -- the two panels share the same
    # button-gated helper and are meant to behave identically.
    trend_subject_key = (team["id"], frozenset(selected_ids), selected_group)
    reset_on_subject_change(
        k(key_prefix, "trend_subject"),
        trend_subject_key,
        {k(key_prefix, "trend_computed"): {}, k(key_prefix, "trend_acronyms"): {}},
    )
    trend_computed_keys = set(st.session_state.get(k(key_prefix, "trend_computed"), {}))

    if narrow:
        trend_metric_panel_col = trend_graph_col = st.container()
    else:
        trend_metric_panel_col, trend_graph_col = st.columns([1, 3])
    with trend_metric_panel_col:
        st.caption("Metrics")
        with st.container(height=240, border=True):
            trend_selected_metrics = []
            for key, acronym in metrics_for_group(selected_group):
                # A green dot marks metrics currently factored into the graph
                # below, distinct from just being checked (e.g. a newly checked
                # metric has no dot until Visualize is pressed again).
                label = full_name_for_metric(key)
                if key in trend_computed_keys:
                    label = f":green[●] {label}"
                if st.checkbox(label, key=k(key_prefix, f"trend_metric_{key}")):
                    trend_selected_metrics.append((key, acronym))
        trend_pressed = st.button("Visualize", key=k(key_prefix, "trend_visualize_btn"), type="primary")

    with trend_graph_col:
        trend_display_metrics = metric_button_state_machine(
            trend_pressed and bool(selected_ids),
            trend_selected_metrics,
            k(key_prefix, "trend_computed"),
            k(key_prefix, "trend_acronyms"),
            lambda key: client.get_aggregate_series(selected_tuple, key, selected_group, perf_start, perf_end),
            spinner_message="Pulling season stats...",
        )
        trend_acronym_by_metric = st.session_state.get(k(key_prefix, "trend_acronyms"), {})

        if not selected_ids:
            st.info("Select one or more players, then press Visualize.")
        elif not trend_selected_metrics:
            st.info("Select one or more metrics, then press Visualize.")
        elif not trend_display_metrics:
            st.info("Press Visualize to plot the checked metrics.")
        else:
            trend_populated = {key: s for key, s in trend_display_metrics.items() if s["years"]}

            if not trend_populated:
                st.info(f"No {perf_start}-{perf_end} season stats for the selected players.")
            else:
                trend_title = f"{team['name']} — {perf_start} to {perf_end}"
                trend_slot = st.empty()
                if trend_pressed:
                    trend_frames = max(len(s["years"]) for s in trend_populated.values())
                    for reveal in range(1, trend_frames):
                        trend_slot.plotly_chart(
                            build_multi_metric_figure(trend_populated, trend_acronym_by_metric, reveal, trend_title),
                            key=k(key_prefix, f"trend_chart_frame_{reveal}"),
                        )
                        time.sleep(REVEAL_FRAME_SECONDS)
                trend_slot.plotly_chart(
                    build_multi_metric_figure(trend_populated, trend_acronym_by_metric, None, trend_title),
                    key=k(key_prefix, "trend_chart_final"),
                )

    st.subheader("Forecast")
    st.caption(
        "Scrubbers 1 and 2 mirror the season range above (read-only) and mark "
        "the training window; drag scrubber 3 to set how far out to forecast."
    )
    mirror_start_col, mirror_end_col = st.columns(2)
    mirror_start_col.number_input(
        "Scrubber 1 (train start)", value=perf_start, disabled=True, key=k(key_prefix, "forecast_mirror_start")
    )
    mirror_end_col.number_input(
        "Scrubber 2 (train end)", value=perf_end, disabled=True, key=k(key_prefix, "forecast_mirror_end")
    )
    forecast_end = pushed_year_control(
        k(key_prefix, "forecast"),
        perf_end,
        FORECAST_MAX_YEAR,
        slider_floor_year=EARLIEST_SEASON,
        label="Scrubber 3 (forecast horizon)",
    )

    # The last-computed forecast is cached per subject (team + exact player
    # selection + group), so switching players/teams doesn't show a stale
    # forecast for the wrong subject until Forecast is pressed again.
    forecast_subject_key = (team["id"], frozenset(selected_ids), selected_group)
    reset_on_subject_change(
        k(key_prefix, "forecast_subject"),
        forecast_subject_key,
        {k(key_prefix, "forecast_computed"): {}, k(key_prefix, "forecast_acronyms"): {}},
    )

    forecast_computed_keys = set(st.session_state.get(k(key_prefix, "forecast_computed"), {}))

    if narrow:
        forecast_metric_panel_col = forecast_graph_col = st.container()
    else:
        forecast_metric_panel_col, forecast_graph_col = st.columns([1, 3])
    with forecast_metric_panel_col:
        st.caption("Metrics")
        with st.container(height=240, border=True):
            forecast_selected_metrics = []
            for key, acronym in metrics_for_group(selected_group):
                label = full_name_for_metric(key)
                if key in forecast_computed_keys:
                    label = f":green[●] {label}"
                if st.checkbox(label, key=k(key_prefix, f"forecast_metric_{key}")):
                    forecast_selected_metrics.append((key, acronym))
        forecast_pressed = st.button("Forecast", type="primary", key=k(key_prefix, "forecast_btn"))

    with forecast_graph_col:
        # Forecasting fits a real model per metric -- this is the only path that
        # ever does that work; every other case inside the shared state machine
        # just filters or clears the last computed result.
        forecast_effective_press = (
            forecast_pressed and bool(selected_ids) and forecast_end > perf_end and bool(forecast_selected_metrics)
        )
        forecast_display_metrics = metric_button_state_machine(
            forecast_effective_press,
            forecast_selected_metrics,
            k(key_prefix, "forecast_computed"),
            k(key_prefix, "forecast_acronyms"),
            lambda key: client.get_aggregate_forecast(
                selected_tuple, key, selected_group, perf_start, perf_end, forecast_end
            ),
            spinner_message="Fitting forecast...",
        )
        if forecast_effective_press:
            st.session_state[k(key_prefix, "forecast_animate")] = True
        forecast_acronym_by_metric = st.session_state.get(k(key_prefix, "forecast_acronyms"), {})

        if not selected_ids:
            st.info("Select one or more players, then press Forecast.")
        elif forecast_end <= perf_end:
            # Scrubber 3 at or before scrubber 2 -- a zero-or-negative-width
            # forecast window. Not just ==: forecast_end is clamped to
            # FORECAST_MAX_YEAR, so it can end up *before* perf_end whenever
            # perf_end itself exceeds that fixed ceiling (e.g. perf_end is the
            # current year and that's later than FORECAST_MAX_YEAR).
            st.info("Widen the forecast horizon: scrubber 3 is at or before scrubber 2.")
        elif not forecast_selected_metrics:
            st.info("Select one or more metrics, then press Forecast.")
        elif not forecast_display_metrics:
            st.info("Press Forecast to compute the checked metrics.")
        else:
            forecast_populated = {key: p for key, p in forecast_display_metrics.items() if p["years"]}

            if not forecast_populated:
                st.info(f"No training data in {perf_start}-{perf_end} for the selected players.")
            else:
                forecast_title = f"{team['name']} — forecast {perf_end} to {forecast_end}"
                forecast_slot = st.empty()
                if st.session_state.get(k(key_prefix, "forecast_animate")):
                    forecast_frames = max(len(p["years"]) for p in forecast_populated.values())
                    for reveal in range(1, forecast_frames):
                        forecast_slot.plotly_chart(
                            build_forecast_figure(forecast_populated, forecast_acronym_by_metric, reveal, forecast_title),
                            key=k(key_prefix, f"forecast_chart_frame_{reveal}"),
                        )
                        time.sleep(REVEAL_FRAME_SECONDS)
                    st.session_state[k(key_prefix, "forecast_animate")] = False
                forecast_slot.plotly_chart(
                    build_forecast_figure(forecast_populated, forecast_acronym_by_metric, None, forecast_title),
                    key=k(key_prefix, "forecast_chart_final"),
                )

    with st.expander("Game Log", key=k(key_prefix, "game_log_expander")):
        if len(selected_ids) != 1:
            st.info("Select exactly one player to see their game log.")
        else:
            game_log_player_id = next(iter(selected_ids))
            game_log_group = "pitching" if bio_by_id.get(game_log_player_id, {}).get("is_pitcher") else "hitting"
            splits = client.get_game_log_splits(game_log_player_id, season, game_log_group)
            if splits:
                rows = []
                for split in splits:
                    row = {"date": split.get("date"), "opponent": split.get("opponent", {}).get("name", "")}
                    row.update(split.get("stat", {}))
                    rows.append(row)
                game_log_df = pd.DataFrame(rows)
                display_columns = [col for col in GAME_LOG_COLUMNS[game_log_group] if col in game_log_df.columns]
                st.dataframe(game_log_df[display_columns], hide_index=True, key=k(key_prefix, "game_log_table"))
            else:
                st.write("No games logged yet this season.")

    # Team Trends (the old per-game rolling offense/defense trajectory) is
    # deliberately commented out, not deleted or ported to this panel model
    # -- it was built for a single team's schedule and needs a
    # multi-player-aware redesign (per-player overlay, or a bulk-group
    # rolling aggregate) before it fits selections that can now be zero,
    # one, or hundreds of players. See the plan's "Team Trends redesign
    # notes" for the two directions considered. Left here (commented, per
    # panel) rather than hoisted out as a single shared block, since -- once
    # redesigned -- it's expected to depend on this panel's own team and
    # player selection, the same as every other section above.
    #
    # st.subheader("Team Trends")
    # offense_col, defense_col = st.columns(2)
    # offense_payload = client.get_team_trajectory(team["id"], season, "offense")
    # defense_payload = client.get_team_trajectory(team["id"], season, "defense")
    # with offense_col:
    #     if offense_payload["x_labels"]:
    #         st.plotly_chart(build_trajectory_figure(offense_payload, team["primary_color"]))
    #     else:
    #         st.info("No completed games yet this season.")
    # with defense_col:
    #     if defense_payload["x_labels"]:
    #         st.plotly_chart(build_trajectory_figure(defense_payload, DEFENSE_COLOR))
    #     else:
    #         st.info("No completed games yet this season.")

    return PanelSelection(team=team, selected_ids=frozenset(selected_ids), bio_by_id=bio_by_id)


teams = client.get_teams()
team_by_name = {team["name"]: team for team in teams}
default_team_name = sorted(team_by_name)[0]

panel_a_col, panel_b_col = st.columns(2)
with panel_a_col:
    panel_a = render_dashboard_panel("a", team_by_name, default_team_name=default_team_name, narrow=True)
with panel_b_col:
    panel_b = render_dashboard_panel("b", team_by_name, default_team_name=None, narrow=True)

with st.sidebar:
    show_news = st.toggle("News Feed", value=False)
    if show_news:
        st.subheader("News")
        # Keyed on Panel A's team only for now -- Panel A always has a team,
        # Panel B may not. Merging both panels' keywords (team + selected
        # player names) into one feed is Phase 7, via PanelSelection above.
        headlines = client.get_news(panel_a.team["keywords"]) if panel_a.team else []
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
