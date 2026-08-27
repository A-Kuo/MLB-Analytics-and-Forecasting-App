"""Baseball Analytics Dashboard -- Streamlit entry point.

A thin router: st.set_page_config and the shared sidebar CSS must run
exactly once, before st.navigation, so they live here rather than in either
page. See pages/analytics_and_forecasts.py (the original single-page
dashboard, renamed as a sibling page) and pages/insights.py (season
leaderboards by metric) for the actual page content.

The News Feed sidebar section is also shared/rendered here, once, AFTER
pg.run() -- st.navigation's pg.run() executes the active page's full
script synchronously before returning control here, and st.session_state
is a global runtime object (not scoped to the child page's own execution),
so whichever page just ran has already written its selected team ids into
st.session_state["news_context"] by the time this module's code below
pg.run() executes. This is what makes News Feed appear identically on both
pages instead of only on Analytics and Forecasts. News is entirely
team-based (no player-name filtering) and Postgres-only -- see
client.get_team_news / macroservice/news_db.py -- so both pages hand off
the exact same shape (just a set of team ids), and this router needs no
per-page branching to render it.
"""
from __future__ import annotations

import streamlit as st

import client
from macroservice.teams import GENERAL_NEWS_HUB_URL, TEAM_BY_ID, team_news_hub_url
from utils.constants import MAX_NEWS_TEAMS, NEWS_LOOKBACK_DAYS
from utils.news_cards import news_card_html

st.set_page_config(page_title="Baseball Analytics Dashboard", layout="wide", initial_sidebar_state="expanded")

# The sidebar only ever needs to hold two nav links plus a compact News
# Feed now, so it's pinned open (no collapse control -- see the two
# collapse/re-expand testids hidden below) and shrunk from its old 270px
# (sized back when this app was a single page with a wider News section).
# [data-testid="collapsedControl"] is the pre-1.4 Streamlit testid for the
# same re-expand control -- kept as a harmless defensive fallback in case a
# deployed Streamlit version differs from what's installed locally.
st.markdown(
    """<style>
    section[data-testid="stSidebar"] {width: 210px !important;}
    [data-testid="stSidebarCollapseButton"] {display: none !important;}
    [data-testid="stExpandSidebarButton"] {display: none !important;}
    [data-testid="collapsedControl"] {display: none !important;}
    </style>""",
    unsafe_allow_html=True,
)

pg = st.navigation(
    [
        st.Page("pages/analytics_and_forecasts.py", title="Analytics and Forecasts", default=True),
        st.Page("pages/insights.py", title="Insights"),
    ]
)
pg.run()

with st.sidebar:
    show_news = st.toggle("News Feed", value=False, key="news_feed_toggle")
    if show_news:
        st.subheader("News")
        # Alphabetical by name, matching pages/insights.py's own
        # convention -- the cap bounds worst-case query size when
        # Insights' default (all 30 teams) is still selected.
        selected_team_ids = st.session_state.get("news_context", {}).get("team_ids", ())
        team_ids = sorted(selected_team_ids, key=lambda tid: TEAM_BY_ID[tid]["name"])[:MAX_NEWS_TEAMS]

        hub_links = {GENERAL_NEWS_HUB_URL: "MLB.com News"}
        for team_id in team_ids:
            hub_links.setdefault(team_news_hub_url(team_id), f"{TEAM_BY_ID[team_id]['name']} News")
        st.caption(" · ".join(f"[{label}]({url})" for url, label in hub_links.items()))
        st.caption(f"Headlines from the last {NEWS_LOOKBACK_DAYS} days.")

        headlines = client.get_team_news(tuple(team_ids), days=NEWS_LOOKBACK_DAYS) if team_ids else []
        if headlines:
            with st.container(height=320):
                for headline in headlines:
                    st.markdown(
                        news_card_html(headline["headline"], headline["link"], headline.get("thumbnail")),
                        unsafe_allow_html=True,
                    )
                    st.divider()
        elif not team_ids:
            st.info("Select a team to see its news.")
        else:
            st.write(
                "No cached news for the selected teams yet. Run "
                "`python scripts/ingest_team_news.py`, or wait for the next scheduled run."
            )
