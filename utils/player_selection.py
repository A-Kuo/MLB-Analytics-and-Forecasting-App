"""Pure, Streamlit-free player-selection logic: per-player flag labels and
the hitting/pitching group used to pick which metric list Aggregate KPI/
Trend/Forecast show.

Kept separate from the Streamlit/session-state wiring in app.py so it's
directly unit-testable with plain Python values -- see
tests/test_player_selection.py.
"""
from __future__ import annotations

import html

from utils.formatters import format_active_years
from utils.positions import color_for_positions, format_position_tag

FLAG_BADGE_STYLE = "display:inline-block;border-radius:12px;padding:4px 10px;font-size:0.85rem;font-weight:500;"


def player_flag_label(bio: dict) -> str:
    """"[SS] Player Name (2015–2020)" -- the shared naming convention used
    in the player-selection dropdown, the selected-player flags, and the
    portrait wall. Multi-position players render as "[SS, 2B] Name (...)";
    a player with more than one active-year span (left and later rejoined
    this team) renders as "Name (2015–2017, 2019–present)".
    """
    positions = bio.get("positions") or []
    name = bio.get("name", "Unknown")
    years = format_active_years(bio.get("active_year_ranges", []))
    tag = format_position_tag(positions)
    return f"{tag} {name} ({years})" if years else f"{tag} {name}"


def flag_badge_html(label: str, color: str = "#555555") -> str:
    return f'<span style="{FLAG_BADGE_STYLE}background:{color}22;border:1px solid {color};">{html.escape(label)}</span>'


def player_flag_html(bio: dict) -> str:
    return flag_badge_html(player_flag_label(bio), color_for_positions(bio.get("positions") or []))


def group_for_selection(selected_ids: frozenset, bio_by_id: dict) -> str:
    """Predominant stat group ("hitting"/"pitching") for a multi-player
    selection. Hitting and pitching metrics can't be meaningfully combined
    (different scales, different meanings -- averaging AVG with ERA is
    nonsensical), so the Aggregate KPI/Trend/Forecast sections show one
    group's metrics for the whole selection: whichever type has more
    players in it. Ties and an empty selection default to hitting.
    """
    pitcher_count = sum(1 for pid in selected_ids if bio_by_id.get(pid, {}).get("is_pitcher", False))
    hitter_count = len(selected_ids) - pitcher_count
    return "pitching" if pitcher_count > hitter_count else "hitting"
