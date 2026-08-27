"""Team flag/badge card builder for the Insights page's team selector.

Deliberately colored (unlike utils/player_cards.py's now-uncolored portrait
cards) -- Austin asked to keep a real, distinct flag/badge display for
teams specifically, diverging from the player selector's multiselect-pill
simplification.

Structurally parallel to utils/player_cards.py: escaped HTML for
st.markdown(unsafe_allow_html=True).
"""
from __future__ import annotations

import html

CARD_WIDTH_PX = 90


def team_flag_html(team: dict) -> str:
    safe_name = html.escape(team["name"])
    safe_abbr = html.escape(team["abbreviation"])
    safe_color = html.escape(team["primary_color"])
    return (
        f'<div style="background:{safe_color};color:#ffffff;border-radius:8px;padding:8px 6px;'
        f'text-align:center;width:{CARD_WIDTH_PX}px;display:inline-block;vertical-align:top;" '
        f'title="{safe_name}">'
        f'<div style="font-size:0.85rem;font-weight:700;">{safe_abbr}</div>'
        "</div>"
    )


def team_flag_wall_html(card_html_list: list[str]) -> str:
    return f'<div style="display:flex;flex-wrap:wrap;gap:8px;">{"".join(card_html_list)}</div>'
