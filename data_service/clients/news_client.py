"""News headline client: NewsAPI when keyed, MLB.com's public RSS feed otherwise."""
from __future__ import annotations

import os

import feedparser
from dotenv import load_dotenv

from backoff import request_with_backoff
from cache import cached

load_dotenv()

NEWS_API_KEY = os.getenv("NEWS_API_KEY")
NEWS_API_URL = "https://newsapi.org/v2/everything"
RSS_FALLBACK_URL = "https://www.mlb.com/feeds/news/rss.xml"
NEWS_TTL_SECONDS = 5 * 60


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
        headlines = [{"title": a["title"], "url": a["url"]} for a in resp.json().get("articles", [])]
    else:
        # feedparser performs its own HTTP fetch; RSS feeds don't rate-limit
        # the way REST APIs do, so the backoff wrapper isn't applied here.
        feed = feedparser.parse(RSS_FALLBACK_URL)
        keywords_lower = [k.lower() for k in keywords]
        headlines = [
            {"title": entry.title, "url": entry.link}
            for entry in feed.entries
            if any(k in entry.title.lower() for k in keywords_lower)
        ]
    return headlines[:limit]
