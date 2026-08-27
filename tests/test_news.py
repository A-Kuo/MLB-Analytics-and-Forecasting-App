from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from unittest.mock import MagicMock, patch

from macroservice.news import (
    _is_within_lookback,
    _normalize_headline,
    _rss_image_by_link,
    fetch_mlb_articles,
    fetch_sbnation_articles,
    fetch_team_articles,
    get_headlines,
)

# Fixed, far-past date rather than "now"-relative -- these two items back
# the image-extraction tests below, which pass a very large `days` window
# so the fixed date always qualifies regardless of when the suite runs.
_OLD_PUBDATE = "Mon, 01 Jan 2024 00:00:00 GMT"

RSS_SAMPLE = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Nimmo says no no!</title>
      <link>https://www.mlb.com/news/nimmo-robs-homer</link>
      <guid isPermaLink="false">abc123</guid>
      <pubDate>{_OLD_PUBDATE}</pubDate>
      <image href="https://img.mlbstatic.com/mlb-images/image/upload/t_16x9/nimmo.jpg"/>
    </item>
    <item>
      <title>Yankees clinch division</title>
      <link>https://www.mlb.com/news/yankees-clinch</link>
      <guid isPermaLink="false">def456</guid>
      <pubDate>{_OLD_PUBDATE}</pubDate>
    </item>
  </channel>
</rss>
""".encode()


def _response(content: bytes):
    resp = MagicMock()
    resp.content = content
    resp.raise_for_status.return_value = None
    return resp


def test_rss_image_by_link_extracts_the_nonstandard_image_tag():
    images = _rss_image_by_link(RSS_SAMPLE)
    assert images["https://www.mlb.com/news/nimmo-robs-homer"] == (
        "https://img.mlbstatic.com/mlb-images/image/upload/t_16x9/nimmo.jpg"
    )


def test_rss_image_by_link_omits_items_without_an_image_tag():
    images = _rss_image_by_link(RSS_SAMPLE)
    assert "https://www.mlb.com/news/yankees-clinch" not in images


def test_rss_image_by_link_returns_empty_dict_on_malformed_xml():
    assert _rss_image_by_link(b"not xml at all") == {}


@patch("macroservice.news.NEWS_API_KEY", None)
@patch("macroservice.news.request_with_backoff")
def test_get_headlines_rss_path_backfills_image_from_raw_xml(mock_request):
    mock_request.return_value = _response(RSS_SAMPLE)
    headlines = get_headlines(["Nimmo", "Yankees"], limit=10, days=36500)
    by_title = {h["title"]: h for h in headlines}
    assert by_title["Nimmo says no no!"]["image"] == (
        "https://img.mlbstatic.com/mlb-images/image/upload/t_16x9/nimmo.jpg"
    )


@patch("macroservice.news.NEWS_API_KEY", None)
@patch("macroservice.news.request_with_backoff")
def test_get_headlines_rss_path_image_is_none_when_no_thumbnail(mock_request):
    mock_request.return_value = _response(RSS_SAMPLE)
    headlines = get_headlines(["Yankees"], limit=10, days=36500)
    assert headlines[0]["image"] is None


@patch("macroservice.news.NEWS_API_KEY", None)
@patch("macroservice.news.request_with_backoff")
def test_get_headlines_rss_path_excludes_entries_older_than_the_lookback(mock_request):
    mock_request.return_value = _response(RSS_SAMPLE)
    # Same fixture, but with the default (small) lookback window instead of
    # the huge one above -- the fixed 2024 pubDate is now outside it, so
    # the real day-window cutoff should drop both entries.
    headlines = get_headlines(["Nimmo", "Yankees"], limit=10, days=7)
    assert headlines == []


@patch("macroservice.news.NEWS_API_KEY", None)
@patch("macroservice.news.request_with_backoff")
def test_get_headlines_rss_path_keeps_recent_entries_within_the_lookback(mock_request):
    recent_pubdate = format_datetime(datetime.now(timezone.utc) - timedelta(days=1))
    sample = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Recent Dodgers news</title>
      <link>https://www.mlb.com/news/recent</link>
      <pubDate>{recent_pubdate}</pubDate>
    </item>
  </channel>
</rss>
""".encode()
    mock_request.return_value = _response(sample)
    # "Recent Dodgers" (not "Dodgers" alone) to avoid colliding with the
    # NewsAPI-path test's cache entry below, which also uses "Dodgers".
    headlines = get_headlines(["Recent Dodgers"], limit=10, days=7)
    assert len(headlines) == 1
    assert headlines[0]["title"] == "Recent Dodgers news"


def test_is_within_lookback_true_for_a_date_at_the_cutoff_boundary():
    cutoff = datetime(2024, 1, 1, tzinfo=timezone.utc)
    entry = MagicMock(published_parsed=(2024, 1, 1, 0, 0, 0, 0, 1, 0))
    assert _is_within_lookback(entry, cutoff) is True


def test_is_within_lookback_false_for_a_date_before_the_cutoff():
    cutoff = datetime(2024, 1, 1, tzinfo=timezone.utc)
    entry = MagicMock(published_parsed=(2023, 12, 31, 0, 0, 0, 0, 1, 0))
    assert _is_within_lookback(entry, cutoff) is False


def test_is_within_lookback_fails_closed_when_date_is_missing():
    cutoff = datetime(2024, 1, 1, tzinfo=timezone.utc)
    entry = MagicMock(published_parsed=None)
    assert _is_within_lookback(entry, cutoff) is False


@patch("macroservice.news.NEWS_API_KEY", "fake-key")
@patch("macroservice.news.request_with_backoff")
def test_get_headlines_newsapi_path_carries_url_to_image(mock_request):
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {
        "articles": [
            {"title": "Test Article", "url": "https://example.com/a", "urlToImage": "https://example.com/a.jpg"},
            {"title": "No Image Article", "url": "https://example.com/b", "urlToImage": None},
        ]
    }
    mock_request.return_value = resp
    # Distinct keywords from the RSS-path tests above -- get_headlines is
    # TTL-cached by its argument tuple, and reusing the same keywords would
    # silently return an earlier test's cached result instead of calling
    # request_with_backoff again.
    headlines = get_headlines(["Dodgers"], limit=10)
    assert headlines[0]["image"] == "https://example.com/a.jpg"
    assert headlines[1]["image"] is None


# ---------------------------------------------------------------------------
# _normalize_headline
# ---------------------------------------------------------------------------


def test_normalize_headline_lowercases_and_collapses_whitespace():
    assert _normalize_headline("  Yankees   Win  Again ") == "yankees win again"


# ---------------------------------------------------------------------------
# fetch_mlb_articles -- ingestion-time, team-scoped, no keyword filtering
# ---------------------------------------------------------------------------

_RECENT_PUBDATE = format_datetime(datetime.now(timezone.utc) - timedelta(hours=1))

MLB_RSS_SAMPLE = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Yankees clinch again</title>
      <link>https://www.mlb.com/yankees/news/clinch</link>
      <pubDate>{_RECENT_PUBDATE}</pubDate>
      <image href="https://img.mlbstatic.com/mlb-images/clinch.jpg"/>
    </item>
  </channel>
</rss>
""".encode()


@patch("macroservice.news.team_news_rss_url")
@patch("macroservice.news.request_with_backoff")
def test_fetch_mlb_articles_tags_source_and_priority(mock_request, mock_url):
    mock_url.return_value = "https://www.mlb.com/yankees/feeds/news/rss.xml"
    mock_request.return_value = _response(MLB_RSS_SAMPLE)
    articles = fetch_mlb_articles(147, days=7)
    assert len(articles) == 1
    assert articles[0]["source"] == "MLB"
    assert articles[0]["headline"] == "Yankees clinch again"
    assert articles[0]["normalized_headline"] == "yankees clinch again"
    assert articles[0]["thumbnail"] == "https://img.mlbstatic.com/mlb-images/clinch.jpg"


@patch("macroservice.news.team_news_rss_url")
def test_fetch_mlb_articles_returns_empty_for_unknown_team(mock_url):
    mock_url.return_value = None
    assert fetch_mlb_articles(999999, days=7) == []


# ---------------------------------------------------------------------------
# fetch_sbnation_articles -- Atom feed, no non-standard image tag
# ---------------------------------------------------------------------------

SBNATION_ATOM_SAMPLE = f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Pinstripe Alley</title>
  <entry>
    <title>Cole dazzles again</title>
    <link href="https://www.pinstripealley.com/news/cole-dazzles" />
    <id>https://www.pinstripealley.com/news/cole-dazzles</id>
    <published>{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}</published>
    <updated>{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}</updated>
  </entry>
</feed>
""".encode()


@patch("macroservice.news.request_with_backoff")
def test_fetch_sbnation_articles_tags_source_and_priority(mock_request):
    mock_request.return_value = _response(SBNATION_ATOM_SAMPLE)
    articles = fetch_sbnation_articles(147, days=7)
    assert len(articles) == 1
    assert articles[0]["source"] == "SBNation"
    assert articles[0]["headline"] == "Cole dazzles again"
    assert articles[0]["link"] == "https://www.pinstripealley.com/news/cole-dazzles"


def test_fetch_sbnation_articles_returns_empty_for_unknown_team():
    assert fetch_sbnation_articles(999999, days=7) == []


@patch("macroservice.news.request_with_backoff")
def test_fetch_sbnation_articles_sends_a_browser_user_agent(mock_request):
    # Confirmed live: SB Nation's CDN 403s a plain requests.get with no
    # User-Agent, unlike MLB.com -- regression guard for that fix.
    mock_request.return_value = _response(SBNATION_ATOM_SAMPLE)
    fetch_sbnation_articles(147, days=7)
    _, kwargs = mock_request.call_args
    assert "Mozilla" in kwargs["headers"]["User-Agent"]


# ---------------------------------------------------------------------------
# fetch_team_articles -- combine, dedupe (keep earliest), priority/recency
# sort, cap at 8
# ---------------------------------------------------------------------------


def _article(source: str, priority: int, headline: str, published_at) -> dict:
    return {
        "source": source,
        "priority": priority,
        "headline": headline,
        "normalized_headline": _normalize_headline(headline),
        "thumbnail": None,
        "link": f"https://example.com/{headline}",
        "published_at": published_at,
    }


@patch("macroservice.news.fetch_sbnation_articles")
@patch("macroservice.news.fetch_mlb_articles")
def test_fetch_team_articles_sorts_by_priority_then_recency(mock_mlb, mock_sbnation):
    now = datetime.now(timezone.utc)
    mock_mlb.return_value = [_article("MLB", 2, "MLB Story", now)]
    mock_sbnation.return_value = [_article("SBNation", 1, "SBNation Story", now - timedelta(hours=1))]
    result = fetch_team_articles(147, days=7)
    # SBNation (priority 1) sorts ahead of MLB (priority 2) even though it
    # published earlier -- priority wins over recency.
    assert [a["source"] for a in result] == ["SBNation", "MLB"]


@patch("macroservice.news.fetch_sbnation_articles")
@patch("macroservice.news.fetch_mlb_articles")
def test_fetch_team_articles_dedupes_exact_headline_keeping_earliest(mock_mlb, mock_sbnation):
    now = datetime.now(timezone.utc)
    earlier = now - timedelta(hours=3)
    mock_mlb.return_value = [_article("MLB", 2, "Same Story", now)]
    mock_sbnation.return_value = [_article("SBNation", 1, "Same Story", earlier)]
    result = fetch_team_articles(147, days=7)
    assert len(result) == 1
    assert result[0]["published_at"] == earlier


@patch("macroservice.news.fetch_sbnation_articles")
@patch("macroservice.news.fetch_mlb_articles")
def test_fetch_team_articles_caps_at_eight(mock_mlb, mock_sbnation):
    now = datetime.now(timezone.utc)
    mock_mlb.return_value = [_article("MLB", 2, f"Story {i}", now - timedelta(hours=i)) for i in range(10)]
    mock_sbnation.return_value = []
    result = fetch_team_articles(147, days=7)
    assert len(result) == 8
