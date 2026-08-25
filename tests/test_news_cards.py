from utils.news_cards import merge_and_cap_keywords, news_card_html


def test_merge_and_cap_keywords_deduplicates_preserving_first_occurrence():
    merged = merge_and_cap_keywords([["Diamondbacks", "Arizona"], ["Arizona", "Paul Goldschmidt"]], max_keywords=10)
    assert merged == ["Diamondbacks", "Arizona", "Paul Goldschmidt"]


def test_merge_and_cap_keywords_earlier_groups_win_priority_at_the_cap():
    merged = merge_and_cap_keywords([["a", "b"], ["c", "d", "e"]], max_keywords=3)
    assert merged == ["a", "b", "c"]


def test_merge_and_cap_keywords_empty_groups_are_fine():
    assert merge_and_cap_keywords([[], []], max_keywords=5) == []


def test_card_includes_escaped_title():
    html_out = news_card_html("Nimmo says <b>no</b> no!", "https://example.com/a", None)
    assert "Nimmo says &lt;b&gt;no&lt;/b&gt; no!" in html_out
    assert "<b>no</b>" not in html_out


def test_card_omits_image_tag_when_no_image():
    html_out = news_card_html("Title", "https://example.com/a", None)
    assert "<img" not in html_out


def test_card_includes_image_tag_when_image_present():
    html_out = news_card_html("Title", "https://example.com/a", "https://example.com/a.jpg")
    assert '<img src="https://example.com/a.jpg"' in html_out


def test_card_rejects_javascript_scheme_url_falls_back_to_hash():
    html_out = news_card_html("Title", "javascript:alert(1)", None)
    assert 'href="#"' in html_out
    assert "javascript:" not in html_out


def test_card_rejects_javascript_scheme_image_omits_img_tag():
    html_out = news_card_html("Title", "https://example.com/a", "javascript:alert(1)")
    assert "<img" not in html_out
    assert "javascript:" not in html_out


def test_card_accepts_http_and_https_urls():
    assert 'href="http://example.com/a"' in news_card_html("T", "http://example.com/a", None)
    assert 'href="https://example.com/a"' in news_card_html("T", "https://example.com/a", None)


def test_card_escapes_quote_in_title_to_prevent_attribute_breakout():
    html_out = news_card_html('"><script>alert(1)</script>', "https://example.com/a", None)
    assert "<script>" not in html_out
