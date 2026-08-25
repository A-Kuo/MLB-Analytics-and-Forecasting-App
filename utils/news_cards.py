"""Renders one news headline as a clickable image+title card.

Streamlit has no native "clickable image card" widget, so this builds a raw
HTML snippet for st.markdown(unsafe_allow_html=True). title/url/image are
externally-sourced (NewsAPI or MLB's RSS feed), so title is HTML-escaped and
url/image are restricted to http(s) schemes before being interpolated --
otherwise a malicious or compromised headline could inject a script or break
out of the href/src attribute.
"""
from __future__ import annotations

import html
from urllib.parse import urlparse

_ALLOWED_SCHEMES = frozenset({"http", "https"})


def _is_safe_url(url: str | None) -> bool:
    if not url:
        return False
    try:
        return urlparse(url).scheme in _ALLOWED_SCHEMES
    except ValueError:
        return False


def merge_and_cap_keywords(keyword_groups: list[list[str]], max_keywords: int) -> list[str]:
    """Flattens ``keyword_groups`` in order, de-duplicating and capping the
    total at ``max_keywords`` -- earlier groups win priority over later ones
    once the cap is hit. Callers pass team keywords ahead of individual
    player names, so a large bulk-group player selection (which can run to
    hundreds of names, see macroservice/roster_history.py) can't blow up
    the news query's size or wipe out the broader team-level signal.
    """
    merged: list[str] = []
    seen: set[str] = set()
    for group in keyword_groups:
        for keyword in group:
            if keyword in seen:
                continue
            seen.add(keyword)
            merged.append(keyword)
            if len(merged) >= max_keywords:
                return merged
    return merged


def news_card_html(title: str, url: str, image: str | None) -> str:
    safe_title = html.escape(title)
    href = html.escape(url) if _is_safe_url(url) else "#"
    image_html = (
        f'<img src="{html.escape(image)}" '
        'style="width:100%;max-height:140px;object-fit:cover;border-radius:4px;margin-bottom:6px;">'
        if _is_safe_url(image)
        else ""
    )
    return (
        f'<a href="{href}" target="_blank" rel="noopener noreferrer" '
        'style="display:block;text-decoration:none;color:inherit;">'
        f"{image_html}"
        f'<div style="font-size:0.85rem;font-weight:500;">{safe_title}</div>'
        "</a>"
    )
