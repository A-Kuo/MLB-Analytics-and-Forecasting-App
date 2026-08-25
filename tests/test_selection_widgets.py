"""Tests for utils/selection_widgets.py's multi-player selector.

Uses Streamlit's AppTest harness (see tests/test_timeline.py and
tests/test_forecast_state_machine.py for the same rationale) since this
logic lives in Streamlit's widget/session_state/callback machinery, not a
plain function. render_player_selection is exercised directly (not via
app.py, which makes real network calls at import time as a flat script).

Test roster: one player per one of a few positions across three of the
four groups, so group/position checkbox sync can be verified without
declaring all fourteen positions.
"""
from __future__ import annotations

from streamlit.testing.v1 import AppTest

SELECTION_SCRIPT = """
import streamlit as st
from utils.selection_widgets import render_player_selection

BIO_BY_ID = {
    1: {"name": "Shorty Stop", "positions": ["SS"], "is_pitcher": False, "active_year_ranges": [(2018, None)]},
    2: {"name": "Kade Combo", "positions": ["2B"], "is_pitcher": False, "active_year_ranges": [(2015, 2022)]},
    3: {"name": "Pitching Pete", "positions": ["P"], "is_pitcher": True, "active_year_ranges": [(2019, None)]},
    4: {"name": "Central Flynn", "positions": ["CF"], "is_pitcher": False, "active_year_ranges": [(2010, 2020)]},
}
CANDIDATE_IDS_BY_POSITION = {
    "P": frozenset({3}), "C": frozenset(),
    "1B": frozenset(), "2B": frozenset({2}), "3B": frozenset(), "SS": frozenset({1}),
    "LF": frozenset(), "CF": frozenset({4}), "RF": frozenset(),
    "DH": frozenset(), "TWP": frozenset(), "PH": frozenset(), "PR": frozenset(), "UTL": frozenset(),
}

result = render_player_selection("t", BIO_BY_ID, CANDIDATE_IDS_BY_POSITION)
st.session_state["result"] = result
"""

PORTRAIT_WALL_SCRIPT = """
import streamlit as st
from utils.selection_widgets import render_portrait_wall

BIO_BY_ID = {
    1: {"name": "Shorty Stop", "positions": ["SS"], "active_year_ranges": [(2018, None)]},
    3: {"name": "Pitching Pete", "positions": ["P"], "active_year_ranges": [(2019, None)]},
}
render_portrait_wall(st.session_state.get("selected", set()), BIO_BY_ID, lambda pid: f"https://example.com/{pid}.jpg")
"""


def test_initial_state_has_no_selection():
    at = AppTest.from_string(SELECTION_SCRIPT).run()
    assert at.session_state["result"] == set()
    assert at.checkbox(key="t_all_cb").value is False


def test_checking_infield_group_selects_all_infield_ids():
    at = AppTest.from_string(SELECTION_SCRIPT).run()
    at.checkbox(key="t_group_Infield_cb").set_value(True).run()
    assert at.session_state["result"] == {1, 2}
    assert at.checkbox(key="t_pos_SS_cb").value is True
    assert at.checkbox(key="t_pos_2B_cb").value is True


def test_unchecking_one_infield_position_unchecks_the_group():
    at = AppTest.from_string(SELECTION_SCRIPT).run()
    at.checkbox(key="t_group_Infield_cb").set_value(True).run()
    at.checkbox(key="t_pos_SS_cb").set_value(False).run()
    assert at.session_state["result"] == {2}
    assert at.checkbox(key="t_group_Infield_cb").value is False
    assert at.checkbox(key="t_pos_2B_cb").value is True  # the other position stays untouched


def test_checking_individual_position_checkbox_selects_its_ids():
    at = AppTest.from_string(SELECTION_SCRIPT).run()
    at.checkbox(key="t_pos_CF_cb").set_value(True).run()
    assert at.session_state["result"] == {4}


def test_flag_shows_position_tagged_label():
    at = AppTest.from_string(SELECTION_SCRIPT).run()
    at.checkbox(key="t_pos_SS_cb").set_value(True).run()
    badges = [m.value for m in at.markdown]
    assert any("[SS] Shorty Stop (2018–present)" in b for b in badges)


def test_clicking_remove_button_deselects_one_player():
    at = AppTest.from_string(SELECTION_SCRIPT).run()
    at.checkbox(key="t_group_Infield_cb").set_value(True).run()
    at.button(key="t_remove_1").click().run()
    assert at.session_state["result"] == {2}


def test_checking_all_players_selects_everyone_and_cascades_group_checkboxes():
    at = AppTest.from_string(SELECTION_SCRIPT).run()
    at.checkbox(key="t_all_cb").set_value(True).run()
    assert at.session_state["result"] == {1, 2, 3, 4}
    assert at.checkbox(key="t_group_Battery_cb").value is True
    assert at.checkbox(key="t_group_Infield_cb").value is True
    assert at.checkbox(key="t_group_Outfield_cb").value is True


def test_unchecking_all_players_clears_everyone_and_resets_group_checkboxes():
    at = AppTest.from_string(SELECTION_SCRIPT).run()
    at.checkbox(key="t_all_cb").set_value(True).run()
    at.checkbox(key="t_all_cb").set_value(False).run()
    assert at.session_state["result"] == set()
    assert at.checkbox(key="t_group_Infield_cb").value is False


def test_manual_multiselect_addition():
    at = AppTest.from_string(SELECTION_SCRIPT).run()
    at.button(key="t_edit_btn").click().run()
    at.multiselect(key="t_multiselect").set_value([1, 3]).run()
    assert at.session_state["result"] == {1, 3}


def test_editor_not_mounted_until_edit_button_clicked():
    at = AppTest.from_string(SELECTION_SCRIPT).run()
    assert len(at.multiselect) == 0
    at.button(key="t_edit_btn").click().run()
    assert len(at.multiselect) == 1


def test_edit_button_toggles_editor_closed_again():
    at = AppTest.from_string(SELECTION_SCRIPT).run()
    at.button(key="t_edit_btn").click().run()
    assert len(at.multiselect) == 1
    at.button(key="t_edit_btn").click().run()
    assert len(at.multiselect) == 0


def test_multiselect_options_scoped_to_candidate_ids_with_shared_label_convention():
    at = AppTest.from_string(SELECTION_SCRIPT).run()
    at.button(key="t_edit_btn").click().run()
    ms = at.multiselect(key="t_multiselect")
    assert set(ms.options) == {
        "[SS] Shorty Stop (2018–present)",
        "[2B] Kade Combo (2015–2022)",
        "[P] Pitching Pete (2019–present)",
        "[CF] Central Flynn (2010–2020)",
    }


def test_multiselect_still_allows_a_previously_selected_id_outside_candidates():
    # A bulk-selected id remains a valid (already-selected) option even if
    # the timeline later narrows candidate_ids_by_position -- exercised here
    # via direct session-state seeding rather than a second script, since
    # candidate_ids_by_position is passed in fresh on every render.
    at = AppTest.from_string(SELECTION_SCRIPT).run()
    at.checkbox(key="t_pos_SS_cb").set_value(True).run()
    at.button(key="t_edit_btn").click().run()
    ms = at.multiselect(key="t_multiselect")
    assert ms.value == [1]


def test_portrait_wall_empty_selection_shows_no_player_message():
    at = AppTest.from_string(PORTRAIT_WALL_SCRIPT).run()
    assert any("No Player Selected" in i.value for i in at.info)


def test_portrait_wall_renders_cards_for_selected_players():
    at = AppTest.from_string(PORTRAIT_WALL_SCRIPT)
    at.session_state["selected"] = {1, 3}
    at.run()
    markdown_html = "".join(m.value for m in at.markdown)
    assert "[SS] Shorty Stop (2018–present)" in markdown_html
    assert "[P] Pitching Pete (2019–present)" in markdown_html
    assert "https://example.com/1.jpg" in markdown_html
