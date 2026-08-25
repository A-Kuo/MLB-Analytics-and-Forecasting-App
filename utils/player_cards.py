"""Portrait-wall card builder: one player's headshot + [position] name
(years active), in a plain neutral-outline card -- no color coding, per
Austin's request that the wall stay uncolored (the same naming convention
appears, colored, on the selection flags -- see utils/player_selection.py).

Structurally parallel to utils/news_cards.py -- escaped HTML for
st.markdown(unsafe_allow_html=True), since player names/years are ultimately
sourced from an external API. The portrait URL itself is a programmatically
templated macroservice.players.headshot_url() call, not raw external text,
so it's escaped for attribute-safety but doesn't need the scheme validation
news_cards.py applies to externally-supplied article URLs.
"""
from __future__ import annotations

import html

BORDER_COLOR = "#cccccc"
CARD_WIDTH_PX = 110


def player_card_html(label: str, portrait_url: str) -> str:
    safe_label = html.escape(label)
    safe_portrait = html.escape(portrait_url)
    return (
        f'<div style="border:1px solid {BORDER_COLOR};border-radius:8px;padding:6px;'
        f'text-align:center;width:{CARD_WIDTH_PX}px;display:inline-block;vertical-align:top;">'
        f'<img src="{safe_portrait}" style="width:100%;border-radius:4px;">'
        f'<div style="font-size:0.75rem;font-weight:600;margin-top:4px;">{safe_label}</div>'
        "</div>"
    )


def portrait_wall_html(card_html_list: list[str]) -> str:
    return f'<div style="display:flex;flex-wrap:wrap;gap:8px;">{"".join(card_html_list)}</div>'
