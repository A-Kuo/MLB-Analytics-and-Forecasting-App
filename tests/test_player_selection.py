from utils.player_selection import flag_badge_html, group_for_selection, resolve_flag_view


def test_individual_selection_shows_every_id_as_outlier():
    view = resolve_flag_view(
        selected_ids=frozenset({1, 2}),
        offense_ids=frozenset({1, 2, 3}),
        defense_ids=frozenset({4}),
        all_ids=frozenset({1, 2, 3, 4}),
    )
    assert view.mode == "individual"
    assert view.label is None
    assert view.outliers == frozenset({1, 2})


def test_all_offense_selected_collapses_to_offense_flag():
    view = resolve_flag_view(
        selected_ids=frozenset({1, 2, 3}),
        offense_ids=frozenset({1, 2, 3}),
        defense_ids=frozenset({4}),
        all_ids=frozenset({1, 2, 3, 4}),
    )
    assert view.mode == "offense"
    assert view.label == "Offense Players"
    assert view.outliers == frozenset()


def test_all_offense_plus_extra_defense_player_shows_outlier():
    view = resolve_flag_view(
        selected_ids=frozenset({1, 2, 3, 4}),
        offense_ids=frozenset({1, 2, 3}),
        defense_ids=frozenset({4, 5}),
        all_ids=frozenset({1, 2, 3, 4, 5}),
    )
    assert view.mode == "offense"
    assert view.label == "Offense Players"
    assert view.outliers == frozenset({4})


def test_all_defense_selected_collapses_to_defense_flag():
    view = resolve_flag_view(
        selected_ids=frozenset({4, 5}),
        offense_ids=frozenset({1, 2, 3}),
        defense_ids=frozenset({4, 5}),
        all_ids=frozenset({1, 2, 3, 4, 5}),
    )
    assert view.mode == "defense"
    assert view.label == "Defense Players"


def test_every_player_selected_collapses_to_all_players_flag_not_offense():
    # An "everyone selected" state is technically also a superset of
    # offense and defense individually -- "all" must win the priority.
    view = resolve_flag_view(
        selected_ids=frozenset({1, 2, 3, 4, 5}),
        offense_ids=frozenset({1, 2, 3}),
        defense_ids=frozenset({4, 5}),
        all_ids=frozenset({1, 2, 3, 4, 5}),
    )
    assert view.mode == "all"
    assert view.label == "All Players"
    assert view.outliers == frozenset()


def test_empty_selection_is_individual_mode_with_no_outliers():
    view = resolve_flag_view(
        selected_ids=frozenset(),
        offense_ids=frozenset({1, 2}),
        defense_ids=frozenset({3}),
        all_ids=frozenset({1, 2, 3}),
    )
    assert view.mode == "individual"
    assert view.outliers == frozenset()


def test_empty_candidate_sets_never_trigger_a_collapse():
    # Empty selection against empty offense/defense/all candidates must not
    # vacuously match "superset of empty set" and falsely report a collapse.
    view = resolve_flag_view(
        selected_ids=frozenset(),
        offense_ids=frozenset(),
        defense_ids=frozenset(),
        all_ids=frozenset(),
    )
    assert view.mode == "individual"


def test_partial_offense_selection_does_not_collapse():
    view = resolve_flag_view(
        selected_ids=frozenset({1, 2}),
        offense_ids=frozenset({1, 2, 3}),
        defense_ids=frozenset({4}),
        all_ids=frozenset({1, 2, 3, 4}),
    )
    assert view.mode == "individual"
    assert view.outliers == frozenset({1, 2})


def test_flag_badge_html_escapes_label():
    badge = flag_badge_html('<script>alert(1)</script>')
    assert "<script>" not in badge
    assert "&lt;script&gt;" in badge


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
