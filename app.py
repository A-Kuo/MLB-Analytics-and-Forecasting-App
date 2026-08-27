"""Baseball Analytics Dashboard -- Streamlit entry point.

A thin router: st.set_page_config and the shared sidebar-width CSS must run
exactly once, before st.navigation, so they live here rather than in either
page. See pages/analytics_and_forecasts.py (the original single-page
dashboard, renamed as a sibling page) and pages/insights.py (season
leaderboards by metric) for the actual page content.
"""
from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Baseball Analytics Dashboard", layout="wide")

# The two side-by-side comparison panels on Analytics and Forecasts need the
# main area's width more than the sidebar does; Streamlit has no
# set_page_config width knob for this, so it's a scoped CSS override (still
# user-resizable by drag, this just changes the default).
st.markdown(
    '<style>section[data-testid="stSidebar"] {width: 270px !important;}</style>',
    unsafe_allow_html=True,
)

pg = st.navigation(
    [
        st.Page("pages/analytics_and_forecasts.py", title="Analytics and Forecasts", default=True),
        st.Page("pages/insights.py", title="Insights"),
    ]
)
pg.run()
