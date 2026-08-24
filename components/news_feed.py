"""Toggleable live news feed, filtered to the selected team's keywords."""
from __future__ import annotations

import panel as pn

from api.news_client import get_team_headlines


def build_news_feed(team_keywords: list[str], visible: bool) -> pn.Column:
    if not visible:
        return pn.Column()

    headlines = get_team_headlines(team_keywords)
    items = (
        [pn.pane.Markdown(f"- [{h['title']}]({h['url']})") for h in headlines]
        if headlines
        else [pn.pane.Markdown("_No recent headlines._")]
    )
    return pn.Column("### News", *items, width=320, styles={"overflow-y": "auto", "max-height": "480px"})
