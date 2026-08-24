"""Sports headline fetcher for the toggleable news feed.

Uses NewsAPI when NEWS_API_KEY is set in the environment; otherwise falls
back to a public MLB RSS feed (no key required) filtered client-side by
team keyword, so the news feed works out of the box.
"""
from __future__ import annotations

import os

import feedparser
import requests
from dotenv import load_dotenv

from api.cache_manager import cached

load_dotenv()

NEWS_API_KEY = os.getenv("NEWS_API_KEY")
NEWS_API_URL = "https://newsapi.org/v2/everything"
RSS_FALLBACK_URL = "https://www.mlb.com/feeds/news/rss.xml"
REQUEST_TIMEOUT = 10
NEWS_TTL_SECONDS = 5 * 60  # matches the README's 5-minute refresh cadence


@cached(ttl_seconds=NEWS_TTL_SECONDS)
def _fetch_rss(feed_url: str) -> list[dict]:
    feed = feedparser.parse(feed_url)
    return [{"title": entry.title, "url": entry.link} for entry in feed.entries]


@cached(ttl_seconds=NEWS_TTL_SECONDS)
def _fetch_newsapi(query: str) -> list[dict]:
    resp = requests.get(
        NEWS_API_URL,
        params={"q": query, "language": "en", "sortBy": "publishedAt", "apiKey": NEWS_API_KEY},
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    return [{"title": a["title"], "url": a["url"]} for a in resp.json().get("articles", [])]


def get_team_headlines(keywords: list[str], limit: int = 10) -> list[dict]:
    """Latest headlines whose title mentions one of ``keywords`` (team name/city)."""
    if NEWS_API_KEY:
        query = " OR ".join(f'"{k}"' for k in keywords)
        headlines = _fetch_newsapi(query)
    else:
        headlines = _fetch_rss(RSS_FALLBACK_URL)
        keywords_lower = [k.lower() for k in keywords]
        headlines = [h for h in headlines if any(k in h["title"].lower() for k in keywords_lower)]
    return headlines[:limit]
