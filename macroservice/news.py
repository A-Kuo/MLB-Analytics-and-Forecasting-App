"""News: two independent things live here.

``get_headlines`` is the original general keyword search (NewsAPI when
keyed, MLB.com's general RSS feed otherwise) -- still used by
macroservice/api.py's standalone ``/news`` route, but no longer called by
the Streamlit dashboard (see below).

Everything else here is ingestion-time source fetching for
scripts/ingest_team_news.py, which writes into the team_news Postgres
table (macroservice/news_db.py). The dashboard's News Feed reads only from
that table (client.get_team_news) -- nothing in this module below
``get_headlines`` ever runs at Streamlit request time; it only runs on the
scheduled ingestion job (.github/workflows/ingest_team_news.yml). Only two
sources are implemented -- see macroservice/config/news_sources.py's
module docstring for the full verification record of why the other
sources from the original design (ESPN, SI, Fox Sports, Yahoo, Twitter)
were deferred rather than built.
"""
from __future__ import annotations

import logging
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

import feedparser
from dotenv import load_dotenv

from macroservice.backoff import request_with_backoff
from macroservice.caching import cached
from macroservice.config.news_sources import SBNATION_URLS, SOURCE_PRIORITY
from macroservice.teams import team_news_rss_url

load_dotenv()

logger = logging.getLogger(__name__)

NEWS_API_KEY = os.getenv("NEWS_API_KEY")
NEWS_API_URL = "https://newsapi.org/v2/everything"
RSS_FALLBACK_URL = "https://www.mlb.com/feeds/news/rss.xml"
NEWS_TTL_SECONDS = 5 * 60
DEFAULT_LOOKBACK_DAYS = 7

# SB Nation's CDN returns 403 for the default python-requests User-Agent
# (confirmed live) -- MLB.com needs no such header, so this is scoped to
# fetch_sbnation_articles specifically, not applied to every request here.
_SBNATION_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}


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


def _is_within_lookback(entry, cutoff: datetime) -> bool:
    """True if ``entry`` (a feedparser entry) has a parseable publish date
    at or after ``cutoff``. An entry with no parseable date is treated as
    outside the window rather than included by default -- this is what
    actually enforces the day-window (previously nothing did; the RSS path
    just took the feed's natural recency, unfiltered), so a malformed date
    should fail closed, not silently bypass the cutoff.
    """
    parsed = getattr(entry, "published_parsed", None)
    if not parsed:
        return False
    published = datetime(*parsed[:6], tzinfo=timezone.utc)
    return published >= cutoff


@cached(ttl_seconds=NEWS_TTL_SECONDS)
def get_headlines(keywords: list[str], limit: int = 10, days: int = DEFAULT_LOOKBACK_DAYS) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    if NEWS_API_KEY:
        query = " OR ".join(f'"{k}"' for k in keywords)
        resp = request_with_backoff(
            "GET",
            NEWS_API_URL,
            params={
                "q": query,
                "language": "en",
                "sortBy": "publishedAt",
                "from": cutoff.date().isoformat(),
                "apiKey": NEWS_API_KEY,
            },
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
            if any(k in entry.title.lower() for k in keywords_lower) and _is_within_lookback(entry, cutoff)
        ]
    return headlines[:limit]


# ---------------------------------------------------------------------------
# Ingestion-time source fetchers for scripts/ingest_team_news.py -- never
# called at Streamlit request time. Each returns rows shaped for
# macroservice/news_db.py's upsert_team_news (missing only ``team_id``,
# which the caller already knows).
# ---------------------------------------------------------------------------


def _normalize_headline(title: str) -> str:
    """Collapses whitespace and case so the same story syndicated with
    trivially different formatting across sources still dedupes -- matches
    the (team_id, normalized_headline) unique constraint on team_news.
    """
    return re.sub(r"\s+", " ", title.strip().lower())


def fetch_mlb_articles(team_id: int, days: int) -> list[dict]:
    """One team's official MLB.com RSS feed (team_news_rss_url, already
    used by the FastAPI-facing hub-link helpers) -- no keyword filtering
    needed, just the lookback-window filter.
    """
    url = team_news_rss_url(team_id)
    if url is None:
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    resp = request_with_backoff("GET", url)
    resp.raise_for_status()
    feed = feedparser.parse(resp.content)
    image_by_link = _rss_image_by_link(resp.content)
    out = []
    for entry in feed.entries:
        if not _is_within_lookback(entry, cutoff):
            continue
        published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
        out.append(
            {
                "source": "MLB",
                "priority": SOURCE_PRIORITY["MLB"],
                "headline": entry.title,
                "normalized_headline": _normalize_headline(entry.title),
                "thumbnail": image_by_link.get(entry.link),
                "link": entry.link,
                "published_at": published,
            }
        )
    return out


def fetch_sbnation_articles(team_id: int, days: int) -> list[dict]:
    """One team's SB Nation blog Atom feed -- confirmed live at
    ``{blog_url}/rss/index.xml`` for every team in SBNATION_URLS (see
    macroservice/config/news_sources.py). feedparser handles Atom the same
    as RSS, so this reuses the exact same parsing shape as fetch_mlb_articles;
    SB Nation's feed has no non-standard image tag, so thumbnails come from
    feedparser's own media/enclosure parsing when present.

    Unlike MLB.com, SB Nation's CDN 403s a plain requests.get with no
    User-Agent (confirmed live) -- a browser-like one is required here,
    not needed anywhere else this codebase talks to.
    """
    base_url = SBNATION_URLS.get(team_id)
    if base_url is None:
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    resp = request_with_backoff("GET", f"{base_url}/rss/index.xml", headers=_SBNATION_HEADERS)
    resp.raise_for_status()
    feed = feedparser.parse(resp.content)
    out = []
    for entry in feed.entries:
        if not _is_within_lookback(entry, cutoff):
            continue
        published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
        thumbnail = None
        if entry.get("media_thumbnail"):
            thumbnail = entry["media_thumbnail"][0].get("url")
        elif entry.get("links"):
            thumbnail = next((link.get("href") for link in entry["links"] if link.get("rel") == "enclosure"), None)
        out.append(
            {
                "source": "SBNation",
                "priority": SOURCE_PRIORITY["SBNation"],
                "headline": entry.title,
                "normalized_headline": _normalize_headline(entry.title),
                "thumbnail": thumbnail,
                "link": entry.link,
                "published_at": published,
            }
        )
    return out


def fetch_team_articles(team_id: int, days: int = DEFAULT_LOOKBACK_DAYS) -> list[dict]:
    """All implemented sources for one team, deduped (an exact-title
    duplicate keeps its earliest-published copy, matching the original
    design) and capped at 8 -- the per-team unit
    scripts/ingest_team_news.py upserts. Plain Python, not pandas --
    ingestion scripts stay light (see requirements-backfill.txt).
    """
    mlb_articles: list[dict] = []
    try:
        mlb_articles = fetch_mlb_articles(team_id, days)
    except Exception as exc:
        logger.warning("MLB.com RSS fetch failed for team %s: %s", team_id, exc)

    sbnation_articles: list[dict] = []
    try:
        sbnation_articles = fetch_sbnation_articles(team_id, days)
    except Exception as exc:
        logger.warning("SB Nation feed fetch failed for team %s: %s", team_id, exc)

    raw = mlb_articles + sbnation_articles

    by_normalized: dict[str, dict] = {}
    for article in raw:
        key = article["normalized_headline"]
        existing = by_normalized.get(key)
        if existing is None or article["published_at"] < existing["published_at"]:
            by_normalized[key] = article

    deduped = sorted(by_normalized.values(), key=lambda a: (a["priority"], -a["published_at"].timestamp()))
    return deduped[:8]
