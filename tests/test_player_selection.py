from utils.player_selection import group_for_selection, player_flag_label


def test_player_flag_label_single_position():
    bio = {"name": "Corbin Carroll", "positions": ["CF"], "active_year_ranges": [(2022, None)]}
    assert player_flag_label(bio) == "[CF] Corbin Carroll (2022–present)"


def test_player_flag_label_multi_position():
    bio = {"name": "Ben Zobrist", "positions": ["2B", "OF"], "active_year_ranges": [(2006, 2019)]}
    assert player_flag_label(bio) == "[2B, OF] Ben Zobrist (2006–2019)"


def test_player_flag_label_staggered_active_years():
    bio = {"name": "Old Timer", "positions": ["SS"], "active_year_ranges": [(1990, 1994), (1998, 2001)]}
    assert player_flag_label(bio) == "[SS] Old Timer (1990–1994, 1998–2001)"


def test_player_flag_label_no_years_omits_parens():
    bio = {"name": "No Data", "positions": ["SS"], "active_year_ranges": []}
    assert player_flag_label(bio) == "[SS] No Data"


def test_player_flag_label_no_positions_shows_placeholder_tag():
    bio = {"name": "Mystery Player", "positions": [], "active_year_ranges": [(2020, None)]}
    assert player_flag_label(bio) == "[?] Mystery Player (2020–present)"


def _bio(pid, is_pitcher):
    return {pid: {"is_pitcher": is_pitcher}}


def test_group_for_selection_more_hitters_gives_hitting():
    bio_by_id = {**_bio(1, False), **_bio(2, False), **_bio(3, True)}
    assert group_for_selection(frozenset({1, 2, 3}), bio_by_id) == "hitting"


def test_group_for_selection_more_pitchers_gives_pitching():
    bio_by_id = {**_bio(1, False), **_bio(2, True), **_bio(3, True)}
    assert group_for_selection(frozenset({1, 2, 3}), bio_by_id) == "pitching"


def test_group_for_selection_tie_defaults_to_hitting():
    bio_by_id = {**_bio(1, False), **_bio(2, True)}
    assert group_for_selection(frozenset({1, 2}), bio_by_id) == "hitting"


def test_group_for_selection_empty_selection_defaults_to_hitting():
    assert group_for_selection(frozenset(), {}) == "hitting"


def test_group_for_selection_missing_bio_treated_as_hitter():
    # An id with no bio entry (data gap) defaults to not-a-pitcher.
    assert group_for_selection(frozenset({99}), {}) == "hitting"
