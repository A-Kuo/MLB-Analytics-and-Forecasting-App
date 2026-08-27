"""Tests for utils/metric_selection.py's shared button-gated state machine.

AppTest is used because both helpers live entirely in Streamlit's
session_state/widget machinery -- see tests/test_timeline.py and
tests/test_forecast_state_machine.py for the same rationale. This exercises
the real utils.metric_selection functions directly (not a duplicated inline
script), covering the subject-change reset half separately from the
button/checkbox half, then a combined script mirroring how
pages/analytics_and_forecasts.py wires Performance Trend's Visualize button.
"""
from __future__ import annotations

from streamlit.testing.v1 import AppTest

SUBJECT_SCRIPT = """
import streamlit as st
from utils.metric_selection import reset_on_subject_change

subject = st.session_state.get("subject_input", "a")
changed = reset_on_subject_change("subject", subject, {"computed": {"stale": True}, "fetch_count": 0})
st.session_state["reset_happened"] = changed
"""


def test_first_run_counts_as_a_subject_change_and_applies_defaults():
    at = AppTest.from_string(SUBJECT_SCRIPT).run()
    assert at.session_state["reset_happened"] is True
    assert at.session_state["computed"] == {"stale": True}


def test_same_subject_on_rerun_does_not_reset():
    at = AppTest.from_string(SUBJECT_SCRIPT).run()
    at.session_state["computed"] = {"real": "value"}
    at.session_state["subject_input"] = "a"  # unchanged
    at.run()
    assert at.session_state["reset_happened"] is False
    assert at.session_state["computed"] == {"real": "value"}


def test_changed_subject_resets_every_default_key():
    at = AppTest.from_string(SUBJECT_SCRIPT).run()
    at.session_state["computed"] = {"real": "value"}
    at.session_state["fetch_count"] = 7
    at.session_state["subject_input"] = "b"  # changed
    at.run()
    assert at.session_state["reset_happened"] is True
    assert at.session_state["computed"] == {"stale": True}
    assert at.session_state["fetch_count"] == 0


STATE_MACHINE_SCRIPT = """
import streamlit as st
from utils.metric_selection import metric_button_state_machine

METRICS = [("era", "ERA"), ("whip", "WHIP"), ("strikeOuts", "K")]

with st.container():
    selected = [(k, a) for k, a in METRICS if st.checkbox(k, key=f"cb_{k}")]
pressed = st.button("Visualize", key="visualize_btn")

fetches = st.session_state.get("fetches", 0)

def compute(key):
    global fetches
    fetches += 1
    return f"payload_for_{key}"

display = metric_button_state_machine(pressed, selected, "computed", "acronyms", compute)
st.session_state["fetches"] = fetches
st.session_state["display_keys"] = sorted(display)
"""


def _display_keys(at: AppTest) -> list[str]:
    return at.session_state["display_keys"]


def _fetches(at: AppTest) -> int:
    return at.session_state["fetches"]


def test_nothing_displayed_before_the_button_is_pressed():
    at = AppTest.from_string(STATE_MACHINE_SCRIPT).run()
    at.checkbox(key="cb_era").set_value(True).run()
    assert _display_keys(at) == []
    assert _fetches(at) == 0


def test_pressing_computes_exactly_the_checked_metrics():
    at = AppTest.from_string(STATE_MACHINE_SCRIPT).run()
    at.checkbox(key="cb_era").set_value(True).run()
    at.checkbox(key="cb_whip").set_value(True).run()
    at.button(key="visualize_btn").click().run()
    assert _display_keys(at) == ["era", "whip"]
    assert _fetches(at) == 2


def test_unchecking_a_computed_metric_drops_it_without_recomputing():
    at = AppTest.from_string(STATE_MACHINE_SCRIPT).run()
    at.checkbox(key="cb_era").set_value(True).run()
    at.checkbox(key="cb_whip").set_value(True).run()
    at.button(key="visualize_btn").click().run()

    at.checkbox(key="cb_whip").set_value(False).run()
    assert _display_keys(at) == ["era"]
    assert _fetches(at) == 2  # no new fetch happened


def test_checking_a_never_computed_metric_clears_the_display():
    at = AppTest.from_string(STATE_MACHINE_SCRIPT).run()
    at.checkbox(key="cb_era").set_value(True).run()
    at.button(key="visualize_btn").click().run()
    assert _display_keys(at) == ["era"]

    at.checkbox(key="cb_strikeOuts").set_value(True).run()
    assert _display_keys(at) == []


COMBINED_SCRIPT = """
import streamlit as st
from utils.metric_selection import metric_button_state_machine, reset_on_subject_change

METRICS = [("era", "ERA"), ("whip", "WHIP")]
subject = st.session_state.get("subject_input", "team-a")
reset_on_subject_change("subject", subject, {"computed": {}, "acronyms": {}})

with st.container():
    selected = [(k, a) for k, a in METRICS if st.checkbox(k, key=f"cb_{k}")]
pressed = st.button("Visualize", key="visualize_btn")

display = metric_button_state_machine(pressed, selected, "computed", "acronyms", lambda k: f"payload_for_{k}")
st.session_state["display_keys"] = sorted(display)
"""


def test_switching_subject_clears_a_previously_visualized_metric():
    at = AppTest.from_string(COMBINED_SCRIPT).run()
    at.checkbox(key="cb_era").set_value(True).run()
    at.button(key="visualize_btn").click().run()
    assert _display_keys(at) == ["era"]

    # Same checkbox stays checked, but the underlying subject (e.g. team or
    # player selection) changed -- the stale result must not keep showing.
    at.session_state["subject_input"] = "team-b"
    at.run()
    assert _display_keys(at) == []
