"""Regression coverage for the Forecast section's Scrubber 1/2 mirrors
(pages/analytics_and_forecasts.py) and the train_end value actually handed
to the forecast fit.

Both scrubbers are disabled sliders that display Timeline's own
perf_start/perf_end live. They previously froze at whichever value Timeline
had on first render (e.g. the default full range's end year) no matter how
far Timeline was dragged afterward: once a *keyed* widget has rendered once,
Streamlit's session_state for that key -- not a later `value=` argument --
is the source of truth on every subsequent rerun. The underlying train_end
plumbing fed to the forecast fit was already correct even while this bug was
live (see the second test below) -- only the on-screen mirrors were stale,
which is exactly what reads as "the forecast is trained on the wrong years"
even though it wasn't. The fix forces each mirror's session_state to the
live value immediately before the widget call, every rerun (AppTest via
streamlit.testing.v1, matching tests/test_timeline.py's rationale for using
it -- this behavior lives in Streamlit's widget/session_state machinery,
not a plain function).

A `key` is required here (not just dropping it) because two of these panels
render side by side in the real page (see render_dashboard_panel's
key_prefix) -- two *keyless* widgets created with identical arguments raise
StreamlitDuplicateElementId, which happens whenever both panels' Timelines
happen to coincide (e.g. both still at their untouched default full range).
"""
from __future__ import annotations

from streamlit.testing.v1 import AppTest

# Mirrors pages/analytics_and_forecasts.py's actual Forecast-section wiring:
# a Timeline range control, two disabled "mirror" sliders force-refreshed via
# session_state, and a forecast_train_end that must always equal perf_end.
MIRROR_SCRIPT = """
import streamlit as st
from utils.timeline import year_range_control

perf_start, perf_end = year_range_control("perf", 1901, 2026, label="Season range")

mirror_start_key = "forecast_mirror_start"
mirror_end_key = "forecast_mirror_end"
st.session_state[mirror_start_key] = perf_start
st.session_state[mirror_end_key] = perf_end
st.slider("Scrubber 1 (train start)", min_value=1901, max_value=2026, disabled=True, key=mirror_start_key)
st.slider("Scrubber 2 (train end)", min_value=1901, max_value=2026, disabled=True, key=mirror_end_key)

forecast_train_end = perf_end
st.session_state["forecast_train_end"] = forecast_train_end
"""

# Two instances of the same widgets, distinct key prefixes -- the real page's
# two side-by-side comparison panels.
TWO_PANEL_SCRIPT = """
import streamlit as st
from utils.timeline import year_range_control

for prefix in ("a", "b"):
    perf_start, perf_end = year_range_control(prefix, 1901, 2026, label="Season range")
    mirror_key = f"{prefix}_forecast_mirror_end"
    st.session_state[mirror_key] = perf_end
    st.slider("Scrubber 2 (train end)", min_value=1901, max_value=2026, disabled=True, key=mirror_key)
"""


def test_train_end_mirror_tracks_timeline_after_dragging_back():
    at = AppTest.from_string(MIRROR_SCRIPT).run()
    assert at.slider(key="forecast_mirror_end").value == 2026

    at.slider(key="perf_range_slider").set_value((1901, 2010)).run()
    assert at.slider(key="forecast_mirror_end").value == 2010
    assert at.slider(key="forecast_mirror_start").value == 1901


def test_forecast_train_end_value_tracks_timeline_after_dragging_back():
    # The value actually fed to the forecast fit, independent of whatever
    # the display mirror shows -- this was never broken, but is worth
    # locking in alongside the display fix so the two can't silently
    # diverge again.
    at = AppTest.from_string(MIRROR_SCRIPT).run()
    at.slider(key="perf_range_slider").set_value((1901, 2010)).run()
    assert at.session_state["forecast_train_end"] == 2010


def test_two_panels_with_coinciding_default_ranges_dont_collide():
    at = AppTest.from_string(TWO_PANEL_SCRIPT).run()
    assert not at.exception
    assert at.slider(key="a_forecast_mirror_end").value == 2026
    assert at.slider(key="b_forecast_mirror_end").value == 2026
