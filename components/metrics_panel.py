"""KPI cards for the selected player's cumulative season stat line."""
from __future__ import annotations

import panel as pn

from utils.formatters import format_stat

HITTING_KPI: list[tuple[str, str]] = [
    ("avg", "AVG"), ("obp", "OBP"), ("slg", "SLG"), ("ops", "OPS"),
    ("homeRuns", "HR"), ("rbi", "RBI"), ("strikeOuts", "K"), ("baseOnBalls", "BB"),
]

PITCHING_KPI: list[tuple[str, str]] = [
    ("era", "ERA"), ("whip", "WHIP"), ("strikeoutsPer9Inn", "K/9"),
    ("walksPer9Inn", "BB/9"), ("wins", "W"), ("losses", "L"),
]

_CARD_STYLE = {
    "background": "#F5F6F8",
    "border-radius": "10px",
    "padding": "12px 18px",
    "text-align": "center",
    "min-width": "84px",
}


def _kpi_card(label: str, value: str) -> pn.Column:
    return pn.Column(
        pn.pane.Markdown(f"**{value}**", styles={"font-size": "22px", "margin": "0"}),
        pn.pane.Markdown(label, styles={"font-size": "12px", "color": "#666", "margin": "0"}),
        styles=_CARD_STYLE,
        margin=(4, 4),
    )


def build_kpi_cards(season_stats: dict, group: str) -> pn.FlexBox:
    kpis = PITCHING_KPI if group == "pitching" else HITTING_KPI
    cards = [_kpi_card(label, format_stat(season_stats.get(key), key)) for key, label in kpis]
    return pn.FlexBox(*cards)
