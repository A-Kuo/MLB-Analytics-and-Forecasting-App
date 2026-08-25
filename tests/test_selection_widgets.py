"""Tests for utils/selection_widgets.py's multi-player selector.

Uses Streamlit's AppTest harness (see tests/test_timeline.py and
tests/test_forecast_state_machine.py for the same rationale) since this
logic lives in Streamlit's widget/session_state/callback machinery, not a
plain function. render_player_selection is exercised directly (not via
app.py, which makes real network calls at import time as a flat script).

Test roster: one player per one of a few positions across three of the
four groups, so position checkbox sync can be verified without declaring
all fourteen positions. There's no group-level checkbox anymore (group
names are plain row labels) -- only "All Players" and individual position
checkboxes are selectable, and the multiselect is the sole per-player
picker/display (no separate flag list).
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


def test_group_names_render_as_plain_labels_not_checkboxes():
    at = AppTest.from_string(SELECTION_SCRIPT).run()
    checkbox_keys = {c.key for c in at.checkbox}
    assert "t_group_Infield_cb" not in checkbox_keys
    markdown_text = "".join(m.value for m in at.markdown)
    assert "**Infield**" in markdown_text
    assert "**Battery**" in markdown_text


def test_checking_individual_position_checkbox_selects_its_ids():
    at = AppTest.from_string(SELECTION_SCRIPT).run()
    at.checkbox(key="t_pos_SS_cb").set_value(True).run()
    assert at.session_state["result"] == {1}


def test_checking_two_positions_in_the_same_group_is_independent():
    at = AppTest.from_string(SELECTION_SCRIPT).run()
    at.checkbox(key="t_pos_SS_cb").set_value(True).run()
    at.checkbox(key="t_pos_2B_cb").set_value(True).run()
    assert at.session_state["result"] == {1, 2}
    at.checkbox(key="t_pos_SS_cb").set_value(False).run()
    assert at.session_state["result"] == {2}  # unaffected by SS being unchecked


def test_checking_all_players_selects_everyone_and_cascades_position_checkboxes():
    at = AppTest.from_string(SELECTION_SCRIPT).run()
    at.checkbox(key="t_all_cb").set_value(True).run()
    assert at.session_state["result"] == {1, 2, 3, 4}
    assert at.checkbox(key="t_pos_SS_cb").value is True
    assert at.checkbox(key="t_pos_P_cb").value is True
    assert at.checkbox(key="t_pos_CF_cb").value is True


def test_unchecking_all_players_clears_everyone_and_resets_position_checkboxes():
    at = AppTest.from_string(SELECTION_SCRIPT).run()
    at.checkbox(key="t_all_cb").set_value(True).run()
    at.checkbox(key="t_all_cb").set_value(False).run()
    assert at.session_state["result"] == set()
    assert at.checkbox(key="t_pos_SS_cb").value is False


def test_multiselect_always_mounted_no_edit_gate():
    at = AppTest.from_string(SELECTION_SCRIPT).run()
    assert len(at.multiselect) == 1
    assert len(at.button) == 0  # no "Edit individual players" button anymore


def test_manual_multiselect_addition():
    at = AppTest.from_string(SELECTION_SCRIPT).run()
    at.multiselect(key="t_multiselect").set_value([1, 3]).run()
    assert at.session_state["result"] == {1, 3}


def test_multiselect_reflects_checkbox_driven_selection():
    at = AppTest.from_string(SELECTION_SCRIPT).run()
    at.checkbox(key="t_pos_SS_cb").set_value(True).run()
    ms = at.multiselect(key="t_multiselect")
    assert ms.value == [1]


def test_multiselect_options_scoped_to_candidate_ids_with_shared_label_convention():
    at = AppTest.from_string(SELECTION_SCRIPT).run()
    ms = at.multiselect(key="t_multiselect")
    assert set(ms.options) == {
        "[SS] Shorty Stop (2018–present)",
        "[2B] Kade Combo (2015–2022)",
        "[P] Pitching Pete (2019–present)",
        "[CF] Central Flynn (2010–2020)",
    }


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
