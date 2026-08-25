"""Tests for utils/timeline.py's year-range widgets.

These use Streamlit's AppTest harness (streamlit.testing.v1) rather than
plain function calls, because year_range_control/pushed_year_control rely
on Streamlit's widget/session_state/callback machinery -- a plain unit
test can't simulate a slider drag or an on_change callback firing.
"""
from __future__ import annotations

from streamlit.testing.v1 import AppTest

YEAR_RANGE_SCRIPT = """
import streamlit as st
from utils.timeline import year_range_control
start, end = year_range_control("perf", 2015, 2020)
"""

COMBINED_SCRIPT = """
import streamlit as st
from utils.timeline import pushed_year_control, year_range_control
start, end = year_range_control("perf", 2015, 2026)
forecast = pushed_year_control("fc", end, 2025, slider_floor_year=2015)
"""


def test_year_range_defaults_to_full_span():
    at = AppTest.from_string(YEAR_RANGE_SCRIPT).run()
    assert at.slider(key="perf_range_slider").value == (2015, 2020)
    assert at.number_input(key="perf_range_start").value == 2015
    assert at.number_input(key="perf_range_end").value == 2020


def test_year_range_slider_drag_syncs_number_inputs():
    at = AppTest.from_string(YEAR_RANGE_SCRIPT).run()
    at.slider(key="perf_range_slider").set_value((2016, 2018)).run()
    assert at.number_input(key="perf_range_start").value == 2016
    assert at.number_input(key="perf_range_end").value == 2018


def test_year_range_valid_number_input_syncs_slider():
    at = AppTest.from_string(YEAR_RANGE_SCRIPT).run()
    at.slider(key="perf_range_slider").set_value((2016, 2018)).run()
    at.number_input(key="perf_range_start").set_value(2017).run()
    assert at.slider(key="perf_range_slider").value == (2017, 2018)


def test_year_range_invalid_start_reverts_instead_of_applying():
    at = AppTest.from_string(YEAR_RANGE_SCRIPT).run()
    at.slider(key="perf_range_slider").set_value((2016, 2018)).run()
    at.number_input(key="perf_range_start").set_value(2017).run()
    # 2019 > current end (2018) -- inverted, must revert rather than apply
    at.number_input(key="perf_range_start").set_value(2019).run()
    assert at.number_input(key="perf_range_start").value == 2017
    assert at.slider(key="perf_range_slider").value == (2017, 2018)


def test_year_range_invalid_end_reverts_instead_of_applying():
    at = AppTest.from_string(YEAR_RANGE_SCRIPT).run()
    at.slider(key="perf_range_slider").set_value((2017, 2018)).run()
    # 2016 < current start (2017) -- inverted, must revert rather than apply
    at.number_input(key="perf_range_end").set_value(2016).run()
    assert at.number_input(key="perf_range_end").value == 2018
    assert at.slider(key="perf_range_slider").value == (2017, 2018)


def test_year_range_allows_same_year_overlap():
    at = AppTest.from_string(YEAR_RANGE_SCRIPT).run()
    at.slider(key="perf_range_slider").set_value((2018, 2018)).run()
    assert at.slider(key="perf_range_slider").value == (2018, 2018)
    assert at.number_input(key="perf_range_start").value == 2018
    assert at.number_input(key="perf_range_end").value == 2018


def test_pushed_control_clamps_initial_value_when_source_exceeds_ceiling():
    # year_range_control("perf", 2015, 2026) defaults its end to 2026, but
    # the forecast ceiling here is 2025 -- must clamp, not crash.
    at = AppTest.from_string(COMBINED_SCRIPT).run()
    assert not at.exception
    assert at.session_state["fc_pushed_value"] == 2025
    assert at.session_state["fc_pushed_input"] == 2025


def test_pushed_control_is_not_pulled_back_when_source_decreases():
    at = AppTest.from_string(COMBINED_SCRIPT).run()
    at.slider(key="perf_range_slider").set_value((2015, 2020)).run()
    at.slider(key="fc_pushed_value").set_value(2022).run()
    at.slider(key="perf_range_slider").set_value((2016, 2019)).run()
    assert at.session_state["fc_pushed_value"] == 2022
    assert at.session_state["fc_pushed_input"] == 2022


def test_pushed_control_is_pushed_forward_when_source_increases_past_it():
    at = AppTest.from_string(COMBINED_SCRIPT).run()
    at.slider(key="perf_range_slider").set_value((2015, 2020)).run()
    at.slider(key="fc_pushed_value").set_value(2022).run()
    at.slider(key="perf_range_slider").set_value((2018, 2023)).run()
    assert at.session_state["fc_pushed_value"] == 2023
    assert at.session_state["fc_pushed_input"] == 2023


def test_pushed_control_valid_input_edit_syncs_slider():
    at = AppTest.from_string(COMBINED_SCRIPT).run()
    at.slider(key="perf_range_slider").set_value((2015, 2020)).run()
    at.number_input(key="fc_pushed_input").set_value(2022).run()
    assert at.session_state["fc_pushed_value"] == 2022


def test_pushed_control_input_below_effective_floor_reverts():
    at = AppTest.from_string(COMBINED_SCRIPT).run()
    at.slider(key="perf_range_slider").set_value((2018, 2023)).run()
    at.number_input(key="fc_pushed_input").set_value(2024).run()
    # 2021 is within the widget's own [2015, 2025] bounds but below the
    # real effective floor (2023) -- must revert, not silently apply.
    at.number_input(key="fc_pushed_input").set_value(2021).run()
    assert at.session_state["fc_pushed_value"] == 2024
    assert at.session_state["fc_pushed_input"] == 2024
