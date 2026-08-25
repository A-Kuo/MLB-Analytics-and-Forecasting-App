"""News headline client: NewsAPI when keyed, MLB.com's public RSS feed otherwise."""
from __future__ import annotations

import os
import xml.etree.ElementTree as ET

import feedparser
from dotenv import load_dotenv

from macroservice.backoff import request_with_backoff
from macroservice.caching import cached

load_dotenv()

NEWS_API_KEY = os.getenv("NEWS_API_KEY")
NEWS_API_URL = "https://newsapi.org/v2/everything"
RSS_FALLBACK_URL = "https://www.mlb.com/feeds/news/rss.xml"
NEWS_TTL_SECONDS = 5 * 60


def _rss_image_by_link(xml_bytes: bytes) -> dict[str, str]:
    """MLB's RSS feed puts each item's thumbnail in a non-standard
    ``<image href="...">`` tag; feedparser doesn't recognize it as a media
    element and silently drops it (confirmed by inspecting the live feed).
    This is a second, lightweight pass over the same raw bytes to recover
    it, keyed by the item's ``<link>`` so it can be matched back onto
    feedparser's parsed entries (``entry.link``).
    """
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return {}

    images_by_link: dict[str, str] = {}
    for item in root.iter("item"):
        link_el = item.find("link")
        image_el = item.find("image")
        if link_el is not None and link_el.text and image_el is not None:
            href = image_el.get("href")
            if href:
                images_by_link[link_el.text.strip()] = href
    return images_by_link


@cached(ttl_seconds=NEWS_TTL_SECONDS)
def get_headlines(keywords: list[str], limit: int = 10) -> list[dict]:
    if NEWS_API_KEY:
        query = " OR ".join(f'"{k}"' for k in keywords)
        resp = request_with_backoff(
            "GET",
            NEWS_API_URL,
            params={"q": query, "language": "en", "sortBy": "publishedAt", "apiKey": NEWS_API_KEY},
        )
        resp.raise_for_status()
        headlines = [
            {"title": a["title"], "url": a["url"], "image": a.get("urlToImage")}
            for a in resp.json().get("articles", [])
        ]
    else:
        resp = request_with_backoff("GET", RSS_FALLBACK_URL)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
        image_by_link = _rss_image_by_link(resp.content)
        keywords_lower = [k.lower() for k in keywords]
        headlines = [
            {"title": entry.title, "url": entry.link, "image": image_by_link.get(entry.link)}
            for entry in feed.entries
            if any(k in entry.title.lower() for k in keywords_lower)
        ]
    return headlines[:limit]
