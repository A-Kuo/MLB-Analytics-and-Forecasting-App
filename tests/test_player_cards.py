from utils.player_cards import player_card_html, portrait_wall_html


def test_card_includes_escaped_name():
    card = player_card_html("O'Brien <b>Jr</b>", "2020–present", "https://example.com/a.jpg", is_pitcher=False)
    assert "&lt;b&gt;" in card
    assert "<b>Jr</b>" not in card


def test_card_includes_active_years_label():
    card = player_card_html("Player One", "2015–2020", "https://example.com/a.jpg", is_pitcher=False)
    assert "2015–2020" in card


def test_offense_card_uses_red_border():
    card = player_card_html("Hitter", "2020–present", "https://example.com/a.jpg", is_pitcher=False)
    assert "#C41E3A" in card
    assert "#1F4E9C" not in card


def test_defense_card_uses_blue_border():
    card = player_card_html("Pitcher", "2020–present", "https://example.com/a.jpg", is_pitcher=True)
    assert "#1F4E9C" in card
    assert "#C41E3A" not in card


def test_card_includes_portrait_image():
    card = player_card_html("Player", "2020–present", "https://example.com/headshot.jpg", is_pitcher=False)
    assert 'src="https://example.com/headshot.jpg"' in card


def test_portrait_wall_wraps_all_cards_in_one_flex_container():
    cards = [player_card_html("A", "2020–present", "https://x/a.jpg", False), player_card_html("B", "2019–2021", "https://x/b.jpg", True)]
    wall = portrait_wall_html(cards)
    assert wall.startswith('<div style="display:flex')
    assert wall.count(">A<") == 1
    assert wall.count(">B<") == 1


def test_portrait_wall_empty_list_still_renders_container():
    wall = portrait_wall_html([])
    assert "display:flex" in wall
