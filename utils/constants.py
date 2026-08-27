"""Shared constants for both dashboard pages
(pages/analytics_and_forecasts.py and pages/insights.py) and the shared
sidebar News Feed rendered by app.py.
"""
from __future__ import annotations

import datetime

EARLIEST_SEASON = 1901  # AL founding -- MLB Stats API's season-stats coverage goes back this far
FORECAST_HORIZON_YEARS = 10

NEWS_LOOKBACK_DAYS = 7
# Insights defaults to all 30 teams selected -- querying news for all 30 on
# every toggle would be a needlessly wide query, so the shared sidebar
# renderer caps to the first MAX_NEWS_TEAMS selected teams (alphabetical by
# name, matching pages/insights.py's own convention).
MAX_NEWS_TEAMS = 10


def forecast_max_year() -> int:
    """Forecast slider's ceiling: 'now + 10 years', computed fresh at
    render time (not a module-level constant, which would only recompute
    once per process -- a long-lived Streamlit Cloud process can run for
    weeks) so it advances automatically with no manual code change.
    """
    return datetime.datetime.now().year + FORECAST_HORIZON_YEARS
