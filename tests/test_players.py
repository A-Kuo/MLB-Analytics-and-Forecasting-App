from macroservice import players


def test_headshot_url_includes_player_id():
    url = players.headshot_url(682998)
    assert "/people/682998/headshot/67/current" in url


def test_headshot_url_default_width():
    url = players.headshot_url(682998)
    assert "w_213," in url


def test_headshot_url_custom_width():
    url = players.headshot_url(682998, width=120)
    assert "w_120," in url


def test_headshot_url_always_returns_a_string_even_for_unknown_id():
    # No network call happens here -- it's a pure URL template, so any int
    # produces a well-formed URL (the CDN's own fallback segment handles
    # unknown ids by serving a generic silhouette instead of erroring).
    url = players.headshot_url(999999999)
    assert url.startswith("https://img.mlbstatic.com/")
