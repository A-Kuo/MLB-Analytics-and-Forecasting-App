"""Team / season / player selectors — the dashboard's primary controls.

v1 scope: team -> season -> individual player only (no team-aggregate or
offense/defense split view; see README roadmap for v1.1).
"""
from __future__ import annotations

import datetime
import json
from pathlib import Path

import panel as pn
import param

from api.mlb_client import get_roster

TEAMS_PATH = Path(__file__).resolve().parent.parent / "config" / "teams.json"
TEAMS: list[dict] = json.loads(TEAMS_PATH.read_text())
TEAM_BY_NAME: dict[str, dict] = {team["name"]: team for team in TEAMS}
CURRENT_SEASON = datetime.date.today().year
EARLIEST_SEASON = 2015


class Sidebar(param.Parameterized):
    team_name = param.Selector(objects=sorted(TEAM_BY_NAME), default=sorted(TEAM_BY_NAME)[0])
    season = param.Selector(
        objects=list(range(EARLIEST_SEASON, CURRENT_SEASON + 1))[::-1],
        default=CURRENT_SEASON,
    )
    player_name = param.Selector(objects=[], default=None)

    def __init__(self, **params):
        super().__init__(**params)
        self._roster_by_name: dict[str, dict] = {}
        self._refresh_roster()

    @param.depends("team_name", "season", watch=True)
    def _refresh_roster(self) -> None:
        team = self.selected_team
        roster = get_roster(team["id"], self.season)
        self._roster_by_name = {player["name"]: player for player in roster}
        names = sorted(self._roster_by_name)
        self.param.player_name.objects = names
        if names and self.player_name not in names:
            self.player_name = names[0]

    @property
    def selected_team(self) -> dict:
        return TEAM_BY_NAME[self.team_name]

    @property
    def selected_player(self) -> dict | None:
        return self._roster_by_name.get(self.player_name)

    def _logo_html(self, team_name: str) -> pn.pane.HTML:
        team = TEAM_BY_NAME[team_name]
        return pn.pane.HTML(
            f'<img src="{team["logo_url"]}" width="72" '
            f'style="display:block;margin:0 auto 8px;" alt="{team["name"]} logo"/>',
            height=88,
        )

    def panel(self) -> pn.Column:
        selectors = pn.Param(
            self.param,
            parameters=["team_name", "season", "player_name"],
            widgets={
                "team_name": {"name": "Team"},
                "season": {"name": "Season"},
                "player_name": {"name": "Player"},
            },
            show_name=False,
            sizing_mode="stretch_width",
        )
        return pn.Column(
            pn.bind(self._logo_html, self.param.team_name),
            selectors,
            width=280,
        )
