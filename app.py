"""Baseball Analytics Dashboard — Panel entry point.

Player trend charts fit a blended SVR/Huber/GaussianProcess ensemble on a
chronological 80/20 holdout (see models/regression.py). Hitters use MLB
Stats API game logs enriched with Statcast batted-ball features (exit
velocity, xBA, hard-hit%); pitchers use pitch-by-pitch Statcast CSW% when
available, falling back to the appearance-level MLB Stats API metrics
(ERA/WHIP/etc.) when Statcast data can't be fetched for that player/season.
A "Team Trends" tab shows 10-game rolling runs scored/allowed for the
selected team, fit with the same ensemble.
"""
from __future__ import annotations

import panel as pn

from api.mlb_client import game_log_dataframe, get_player_season_stats, team_schedule_dataframe
from api.statcast_client import get_batter_batted_balls, get_pitcher_pitches
from components.game_log import build_game_log
from components.line_chart import build_hitter_chart, build_pitcher_csw_chart, build_pitcher_legacy_chart
from components.metrics_panel import build_kpi_cards
from components.news_feed import build_news_feed
from components.sidebar import Sidebar
from components.team_trends import build_team_defense_chart, build_team_offense_chart
from utils.features import build_hitter_feature_frame, build_pitcher_csw_frame
from utils.filters import GAME_LOG_COLUMNS, metrics_for_group, stat_group_for_position

pn.extension("plotly", "tabulator")

sidebar = Sidebar()
news_toggle = pn.widgets.Toggle(name="News Feed", value=False, button_type="primary")
metric_select = pn.widgets.Select(name="Metric", options={})


def _refresh_metric_options(event=None) -> None:
    player = sidebar.selected_player
    if not player:
        return
    group = stat_group_for_position(player["position"])
    options = {label: key for key, label in metrics_for_group(group)}
    metric_select.options = options
    metric_select.value = next(iter(options.values()))


sidebar.param.watch(_refresh_metric_options, "player_name")
_refresh_metric_options()


@pn.depends(sidebar.param.player_name, sidebar.param.season)
def kpi_view(player_name, season):
    player = sidebar.selected_player
    if not player:
        return pn.pane.Markdown("_Select a player._")
    group = stat_group_for_position(player["position"])
    stats = get_player_season_stats(player["id"], season, group)
    return build_kpi_cards(stats, group)


@pn.depends(sidebar.param.player_name, sidebar.param.season, metric_select.param.value)
def chart_view(player_name, season, metric):
    player = sidebar.selected_player
    if not player:
        return pn.pane.Markdown("_Select a player and metric._")

    group = stat_group_for_position(player["position"])
    team_color = sidebar.selected_team["primary_color"]

    if group == "pitching":
        pitches = get_pitcher_pitches(player["id"], season)
        if not pitches.empty:
            frame = build_pitcher_csw_frame(pitches)
            fig = build_pitcher_csw_chart(frame, team_color)
            return pn.pane.Plotly(fig, height=440, sizing_mode="stretch_width")

        # Statcast unavailable for this pitcher/season -- fall back to the
        # appearance-level MLB Stats API metric the dropdown already offers.
        label_by_key = {key: label for label, key in metric_select.options.items()}
        label = label_by_key.get(metric)
        if label is None:
            return pn.pane.Markdown("_Loading…_")
        df = game_log_dataframe(player["id"], season, group)
        if df.empty or metric not in df.columns:
            return pn.pane.Markdown(f"_No {season} game log yet for {player_name}._")
        fig = build_pitcher_legacy_chart(df, metric, label, team_color)
        return pn.pane.Plotly(fig, height=440, sizing_mode="stretch_width")

    label_by_key = {key: label for label, key in metric_select.options.items()}
    label = label_by_key.get(metric)
    if label is None:
        return pn.pane.Markdown("_Loading…_")
    df = game_log_dataframe(player["id"], season, group)
    if df.empty or metric not in df.columns:
        return pn.pane.Markdown(f"_No {season} game log yet for {player_name}._")

    batted_balls = get_batter_batted_balls(player["id"], season)
    frame = build_hitter_feature_frame(df, batted_balls, metric=metric)
    fig = build_hitter_chart(frame, metric, label, team_color)
    return pn.pane.Plotly(fig, height=440, sizing_mode="stretch_width")


@pn.depends(sidebar.param.player_name, sidebar.param.season)
def game_log_view(player_name, season):
    player = sidebar.selected_player
    if not player:
        return pn.pane.Markdown("_Select a player._")
    group = stat_group_for_position(player["position"])
    df = game_log_dataframe(player["id"], season, group)
    if df.empty:
        return pn.pane.Markdown("_No games logged yet this season._")
    return build_game_log(df, GAME_LOG_COLUMNS[group])


@pn.depends(sidebar.param.team_name, news_toggle.param.value)
def news_view(team_name, show_news):
    return build_news_feed(sidebar.selected_team["keywords"], show_news)


@pn.depends(sidebar.param.team_name, sidebar.param.season)
def team_offense_view(team_name, season):
    team = sidebar.selected_team
    schedule = team_schedule_dataframe(team["id"], season)
    if schedule.empty:
        return pn.pane.Markdown("_No completed games yet this season._")
    fig = build_team_offense_chart(schedule, team["primary_color"])
    return pn.pane.Plotly(fig, height=380, sizing_mode="stretch_width")


@pn.depends(sidebar.param.team_name, sidebar.param.season)
def team_defense_view(team_name, season):
    team = sidebar.selected_team
    schedule = team_schedule_dataframe(team["id"], season)
    if schedule.empty:
        return pn.pane.Markdown("_No completed games yet this season._")
    fig = build_team_defense_chart(schedule, team["primary_color"])
    return pn.pane.Plotly(fig, height=380, sizing_mode="stretch_width")


player_tab = pn.Column(
    pn.Row(
        pn.Column("## Season KPIs", kpi_view, sizing_mode="stretch_width"),
        news_view,
    ),
    pn.Column("## Performance Trend", metric_select, chart_view),
    pn.Accordion(("Game Log", game_log_view)),
)

team_trends_tab = pn.Column(
    "## Team Offense — Rolling Runs Scored",
    team_offense_view,
    "## Team Defense — Rolling Runs Allowed",
    team_defense_view,
)

template = pn.template.FastListTemplate(
    title="Baseball Analytics Dashboard",
    sidebar=[sidebar.panel, pn.layout.Divider(), news_toggle],
    main=[pn.Tabs(("Player", player_tab), ("Team Trends", team_trends_tab))],
    header_background="#002D72",
)

template.servable()
