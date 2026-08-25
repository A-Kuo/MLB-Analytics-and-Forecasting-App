from utils.player_cards import player_card_html, portrait_wall_html


def test_card_includes_escaped_label():
    card = player_card_html("[SS] O'Brien <b>Jr</b> (2020–present)", "https://example.com/a.jpg")
    assert "&lt;b&gt;" in card
    assert "<b>Jr</b>" not in card


def test_card_includes_full_label():
    card = player_card_html("[SS] Player One (2015–2020)", "https://example.com/a.jpg")
    assert "[SS] Player One (2015–2020)" in card


def test_card_has_no_color_coded_border():
    # The portrait wall is deliberately plain -- color coding lives on the
    # selection flags instead (see utils/player_selection.py).
    card = player_card_html("[SS] Hitter (2020–present)", "https://example.com/a.jpg")
    assert "#C41E3A" not in card
    assert "#1F4E9C" not in card


def test_card_includes_portrait_image():
    card = player_card_html("[P] Player (2020–present)", "https://example.com/headshot.jpg")
    assert 'src="https://example.com/headshot.jpg"' in card


def test_portrait_wall_wraps_all_cards_in_one_flex_container():
    cards = [player_card_html("[SS] A (2020–present)", "https://x/a.jpg"), player_card_html("[P] B (2019–2021)", "https://x/b.jpg")]
    wall = portrait_wall_html(cards)
    assert wall.startswith('<div style="display:flex')
    assert wall.count("A (2020") == 1
    assert wall.count("B (2019") == 1


def test_portrait_wall_empty_list_still_renders_container():
    wall = portrait_wall_html([])
    assert "display:flex" in wall
