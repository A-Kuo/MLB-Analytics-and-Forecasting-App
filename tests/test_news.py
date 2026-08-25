from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from unittest.mock import MagicMock, patch

from macroservice.news import _is_within_lookback, _rss_image_by_link, get_headlines

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
