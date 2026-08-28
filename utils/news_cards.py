"""Renders one news headline as a clickable image+title card.

Streamlit has no native "clickable image card" widget, so this builds a raw
HTML snippet for st.markdown(unsafe_allow_html=True). title/url/image are
externally-sourced (MLB.com's and SB Nation's feeds, pre-ingested into
Postgres by scripts/ingest_team_news.py -- see macroservice/news_db.py), so
title is HTML-escaped and url/image are restricted to http(s) schemes
before being interpolated -- otherwise a malicious or compromised headline
could inject a script or break out of the href/src attribute.
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


def news_card_html(title: str, url: str, image: str | None) -> str:
    safe_title = html.escape(title)
    href = html.escape(url) if _is_safe_url(url) else "#"
    image_html = (
        f'<img src="{html.escape(image)}" '
        'style="width:100%;max-height:120px;object-fit:cover;border-radius:4px;margin-bottom:8px;">'
        if _is_safe_url(image)
        else ""
    )
    # Entire card (thumbnail + headline) is clickable. Hover feedback comes
    # from the "mlb-news-card" class + a global :hover rule (app.py) rather
    # than inline onmouseover/onmouseout handlers -- those require careful
    # attribute-spacing that's easy to get wrong (a missing space between
    # adjacent attributes silently breaks Streamlit's HTML-block parsing,
    # which then renders the whole tag as literal escaped text instead of
    # a link) and some sanitizers strip inline event-handler attributes
    # outright.
    return (
        f'<a href="{href}" target="_blank" rel="noopener noreferrer" class="mlb-news-card" '
        'style="display:block;text-decoration:none;color:inherit;padding:8px;border-radius:4px;">'
        f"{image_html}"
        f'<div style="font-size:0.85rem;font-weight:500;line-height:1.3;">{safe_title}</div>'
        "</a>"
    )
