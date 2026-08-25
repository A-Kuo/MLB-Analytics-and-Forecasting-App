from unittest.mock import MagicMock, patch

from macroservice.news import _rss_image_by_link, get_headlines

RSS_SAMPLE = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Nimmo says no no!</title>
      <link>https://www.mlb.com/news/nimmo-robs-homer</link>
      <guid isPermaLink="false">abc123</guid>
      <image href="https://img.mlbstatic.com/mlb-images/image/upload/t_16x9/nimmo.jpg"/>
    </item>
    <item>
      <title>Yankees clinch division</title>
      <link>https://www.mlb.com/news/yankees-clinch</link>
      <guid isPermaLink="false">def456</guid>
    </item>
  </channel>
</rss>
"""


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
    headlines = get_headlines(["Nimmo", "Yankees"], limit=10)
    by_title = {h["title"]: h for h in headlines}
    assert by_title["Nimmo says no no!"]["image"] == (
        "https://img.mlbstatic.com/mlb-images/image/upload/t_16x9/nimmo.jpg"
    )


@patch("macroservice.news.NEWS_API_KEY", None)
@patch("macroservice.news.request_with_backoff")
def test_get_headlines_rss_path_image_is_none_when_no_thumbnail(mock_request):
    mock_request.return_value = _response(RSS_SAMPLE)
    headlines = get_headlines(["Yankees"], limit=10)
    assert headlines[0]["image"] is None


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
