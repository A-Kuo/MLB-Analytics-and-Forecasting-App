"""Tests for utils/selection_widgets.py's multi-player selector.

Uses Streamlit's AppTest harness (see tests/test_timeline.py and
tests/test_forecast_state_machine.py for the same rationale) since this
logic lives in Streamlit's widget/session_state/callback machinery, not a
plain function. render_player_selection is exercised directly (not via
app.py, which makes real network calls at import time as a flat script).
"""
from __future__ import annotations

from streamlit.testing.v1 import AppTest

SELECTION_SCRIPT = """
import streamlit as st
from utils.selection_widgets import render_player_selection

BIO_BY_ID = {
    1: {"name": "Alice Hitter", "is_pitcher": False, "active_years_label": "2018-present"},
    2: {"name": "Bob Hitter", "is_pitcher": False, "active_years_label": "2015-2022"},
    3: {"name": "Cara Pitcher", "is_pitcher": True, "active_years_label": "2019-present"},
    4: {"name": "Dan Pitcher", "is_pitcher": True, "active_years_label": "2010-2020"},
}
OFFENSE_IDS = frozenset({1, 2})
DEFENSE_IDS = frozenset({3, 4})
ALL_IDS = OFFENSE_IDS | DEFENSE_IDS

result = render_player_selection("t", BIO_BY_ID, OFFENSE_IDS, DEFENSE_IDS, ALL_IDS)
st.session_state["result"] = result
"""

PORTRAIT_WALL_SCRIPT = """
import streamlit as st
from utils.selection_widgets import render_portrait_wall

BIO_BY_ID = {
    1: {"name": "Alice Hitter", "is_pitcher": False, "active_years_label": "2018-present"},
    3: {"name": "Cara Pitcher", "is_pitcher": True, "active_years_label": "2019-present"},
}
render_portrait_wall(st.session_state.get("selected", set()), BIO_BY_ID, lambda pid: f"https://example.com/{pid}.jpg")
"""


def test_initial_state_has_no_selection():
    at = AppTest.from_string(SELECTION_SCRIPT).run()
    assert at.session_state["result"] == set()
    assert at.checkbox(key="t_offense_cb").value is False


def test_checking_offense_selects_all_offense_ids():
    at = AppTest.from_string(SELECTION_SCRIPT).run()
    at.checkbox(key="t_offense_cb").set_value(True).run()
    assert at.session_state["result"] == {1, 2}


def test_offense_selection_collapses_to_one_flag():
    at = AppTest.from_string(SELECTION_SCRIPT).run()
    at.checkbox(key="t_offense_cb").set_value(True).run()
    badges = [m.value for m in at.markdown]
    assert any("Offense Players" in b for b in badges)
    assert not any("Alice Hitter" in b for b in badges)


def test_clicking_group_remove_button_clears_selection_and_unchecks_box():
    at = AppTest.from_string(SELECTION_SCRIPT).run()
    at.checkbox(key="t_offense_cb").set_value(True).run()
    at.button(key="t_remove_group").click().run()
    assert at.session_state["result"] == set()
    assert at.checkbox(key="t_offense_cb").value is False


def test_manual_multiselect_addition():
    at = AppTest.from_string(SELECTION_SCRIPT).run()
    at.button(key="t_edit_btn").click().run()
    at.multiselect(key="t_multiselect").set_value([1, 3]).run()
    assert at.session_state["result"] == {1, 3}


def test_offense_plus_one_outlier_shows_group_flag_and_outlier_flag():
    at = AppTest.from_string(SELECTION_SCRIPT).run()
    at.button(key="t_edit_btn").click().run()
    at.multiselect(key="t_multiselect").set_value([1, 3]).run()
    at.checkbox(key="t_offense_cb").set_value(True).run()

    assert at.session_state["result"] == {1, 2, 3}
    badges = [m.value for m in at.markdown]
    assert any("Offense Players" in b for b in badges)
    assert any("Cara Pitcher" in b for b in badges)
    remove_keys = {b.key for b in at.button}
    assert "t_remove_group" in remove_keys
    assert "t_remove_3" in remove_keys


def test_removing_individual_outlier_leaves_group_intact():
    at = AppTest.from_string(SELECTION_SCRIPT).run()
    at.button(key="t_edit_btn").click().run()
    at.multiselect(key="t_multiselect").set_value([1, 3]).run()
    at.checkbox(key="t_offense_cb").set_value(True).run()
    at.button(key="t_remove_3").click().run()

    assert at.session_state["result"] == {1, 2}
    assert at.checkbox(key="t_offense_cb").value is True  # group untouched


def test_offense_and_defense_together_collapse_to_all_players():
    at = AppTest.from_string(SELECTION_SCRIPT).run()
    at.checkbox(key="t_offense_cb").set_value(True).run()
    at.checkbox(key="t_defense_cb").set_value(True).run()

    assert at.session_state["result"] == {1, 2, 3, 4}
    assert at.checkbox(key="t_all_cb").value is True
    badges = [m.value for m in at.markdown]
    assert any("All Players" in b for b in badges)


def test_unchecking_all_players_clears_everyone_and_resets_sub_checkboxes():
    at = AppTest.from_string(SELECTION_SCRIPT).run()
    at.checkbox(key="t_offense_cb").set_value(True).run()
    at.checkbox(key="t_defense_cb").set_value(True).run()
    at.checkbox(key="t_all_cb").set_value(False).run()

    assert at.session_state["result"] == set()
    assert at.checkbox(key="t_offense_cb").value is False
    assert at.checkbox(key="t_defense_cb").value is False


def test_removing_one_offense_player_via_flag_auto_unchecks_offense_box():
    at = AppTest.from_string(SELECTION_SCRIPT).run()
    at.checkbox(key="t_offense_cb").set_value(True).run()
    # With the group collapsed, the per-player remove button isn't rendered
    # directly -- open the editor and deselect one manually instead, which
    # is the equivalent "partial removal" path.
    at.button(key="t_edit_btn").click().run()
    at.multiselect(key="t_multiselect").set_value([1]).run()
    assert at.session_state["result"] == {1}
    assert at.checkbox(key="t_offense_cb").value is False  # no longer a superset


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


def test_portrait_wall_empty_selection_shows_no_player_message():
    at = AppTest.from_string(PORTRAIT_WALL_SCRIPT).run()
    assert any("No Player Selected" in i.value for i in at.info)


def test_portrait_wall_renders_cards_for_selected_players():
    at = AppTest.from_string(PORTRAIT_WALL_SCRIPT)
    at.session_state["selected"] = {1, 3}
    at.run()
    markdown_html = "".join(m.value for m in at.markdown)
    assert "Alice Hitter" in markdown_html
    assert "Cara Pitcher" in markdown_html
    assert "https://example.com/1.jpg" in markdown_html
