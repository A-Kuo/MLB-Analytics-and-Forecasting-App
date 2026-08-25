"""Tests for the Forecast section's checkbox/compute state machine.

This mirrors (as a minimal standalone script) the exact session-state
pattern used in app.py's Forecast section: compute only on button press;
unchecking a metric drops it from the display without recomputing; checking
a metric that was never computed clears the display until Forecast is
pressed again. AppTest is used because this behavior lives entirely in
Streamlit's session_state/callback machinery, not in a plain function --
see tests/test_timeline.py for the same rationale.
"""
from __future__ import annotations

from streamlit.testing.v1 import AppTest

SCRIPT = """
import streamlit as st

METRICS = ["era", "whip", "strikeOuts"]

with st.container():
    selected = [k for k in METRICS if st.checkbox(k, key=f"cb_{k}")]
pressed = st.button("Forecast", key="forecast_btn")

current_keys = set(selected)
computed = st.session_state.get("computed", {})

if pressed and selected:
    computed = {k: f"payload_for_{k}" for k in selected}
    st.session_state["computed"] = computed
    st.session_state["fetch_count"] = st.session_state.get("fetch_count", 0) + len(selected)
elif current_keys - computed.keys():
    computed = {}
    st.session_state["computed"] = {}

display = {k: computed[k] for k in current_keys if k in computed}
st.session_state["display_keys"] = sorted(display)
"""


def _display_keys(at: AppTest) -> list[str]:
    return at.session_state["display_keys"]


def _fetch_count(at: AppTest) -> int:
    return at.session_state["fetch_count"] if "fetch_count" in at.session_state else 0


def test_nothing_displayed_before_forecast_is_pressed():
    at = AppTest.from_string(SCRIPT).run()
    at.checkbox(key="cb_era").set_value(True).run()
    assert _display_keys(at) == []
    assert _fetch_count(at) == 0


def test_pressing_forecast_computes_exactly_the_checked_metrics():
    at = AppTest.from_string(SCRIPT).run()
    at.checkbox(key="cb_era").set_value(True).run()
    at.checkbox(key="cb_whip").set_value(True).run()
    at.button(key="forecast_btn").click().run()
    assert _display_keys(at) == ["era", "whip"]
    assert _fetch_count(at) == 2


def test_unchecking_a_computed_metric_drops_it_without_recomputing():
    at = AppTest.from_string(SCRIPT).run()
    at.checkbox(key="cb_era").set_value(True).run()
    at.checkbox(key="cb_whip").set_value(True).run()
    at.button(key="forecast_btn").click().run()
    assert _fetch_count(at) == 2

    at.checkbox(key="cb_whip").set_value(False).run()
    assert _display_keys(at) == ["era"]
    assert _fetch_count(at) == 2  # no new fetch happened


def test_checking_a_never_computed_metric_clears_the_display():
    at = AppTest.from_string(SCRIPT).run()
    at.checkbox(key="cb_era").set_value(True).run()
    at.button(key="forecast_btn").click().run()
    assert _display_keys(at) == ["era"]

    # strikeOuts was never part of a Forecast press -- checking it should
    # clear everything, not silently add it or keep showing the stale era line.
    at.checkbox(key="cb_strikeOuts").set_value(True).run()
    assert _display_keys(at) == []


def test_pressing_forecast_again_recomputes_for_the_new_full_selection():
    at = AppTest.from_string(SCRIPT).run()
    at.checkbox(key="cb_era").set_value(True).run()
    at.button(key="forecast_btn").click().run()
    at.checkbox(key="cb_strikeOuts").set_value(True).run()
    assert _display_keys(at) == []  # cleared by the previous test's scenario

    at.button(key="forecast_btn").click().run()
    assert _display_keys(at) == ["era", "strikeOuts"]
    assert _fetch_count(at) == 3  # 1 (era alone) + 2 (era, strikeOuts) across the two presses


def test_rechecking_a_previously_computed_metric_reappears_without_a_new_press():
    at = AppTest.from_string(SCRIPT).run()
    at.checkbox(key="cb_era").set_value(True).run()
    at.checkbox(key="cb_whip").set_value(True).run()
    at.button(key="forecast_btn").click().run()
    at.checkbox(key="cb_whip").set_value(False).run()
    assert _display_keys(at) == ["era"]

    # whip is still in the cache from the earlier press -- rechecking it
    # should bring it back without needing Forecast pressed again.
    at.checkbox(key="cb_whip").set_value(True).run()
    assert _display_keys(at) == ["era", "whip"]
    assert _fetch_count(at) == 2  # unchanged -- no recompute triggered
