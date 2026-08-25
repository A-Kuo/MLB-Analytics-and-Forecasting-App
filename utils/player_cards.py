"""Portrait-wall card builder: one player's headshot + name + active-years,
in a colored-outline card (red = offense, blue = defense).

Structurally parallel to utils/news_cards.py -- escaped HTML for
st.markdown(unsafe_allow_html=True), since player names/years are ultimately
sourced from an external API. The portrait URL itself is a programmatically
templated macroservice.players.headshot_url() call, not raw external text,
so it's escaped for attribute-safety but doesn't need the scheme validation
news_cards.py applies to externally-supplied article URLs.
"""
from __future__ import annotations

import html

OFFENSE_BORDER_COLOR = "#C41E3A"  # red
DEFENSE_BORDER_COLOR = "#1F4E9C"  # blue
CARD_WIDTH_PX = 110


def player_card_html(name: str, active_years_label: str, portrait_url: str, is_pitcher: bool) -> str:
    border_color = DEFENSE_BORDER_COLOR if is_pitcher else OFFENSE_BORDER_COLOR
    safe_name = html.escape(name)
    safe_years = html.escape(active_years_label)
    safe_portrait = html.escape(portrait_url)
    return (
        f'<div style="border:2px solid {border_color};border-radius:8px;padding:6px;'
        f'text-align:center;width:{CARD_WIDTH_PX}px;display:inline-block;vertical-align:top;">'
        f'<img src="{safe_portrait}" style="width:100%;border-radius:4px;">'
        f'<div style="font-size:0.78rem;font-weight:600;margin-top:4px;">{safe_name}</div>'
        f'<div style="font-size:0.7rem;color:#666;">{safe_years}</div>'
        "</div>"
    )


def portrait_wall_html(card_html_list: list[str]) -> str:
    return f'<div style="display:flex;flex-wrap:wrap;gap:8px;">{"".join(card_html_list)}</div>'
