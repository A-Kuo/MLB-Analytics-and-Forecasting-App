"""Pure, Streamlit-free player-selection logic: the "collapse to one flag"
detection behind the Offense/Defense/All-Players bulk-selection checkboxes.

Kept separate from the Streamlit/session-state wiring in app.py so it's
directly unit-testable with plain Python sets -- see tests/test_player_selection.py.
"""
from __future__ import annotations

import html
from dataclasses import dataclass

FLAG_BADGE_STYLE = (
    "display:inline-block;background:#eef1f5;border-radius:12px;"
    "padding:4px 10px;font-size:0.85rem;font-weight:500;"
)


@dataclass(frozen=True)
class FlagView:
    mode: str  # "all" | "offense" | "defense" | "individual"
    label: str | None  # None when mode == "individual"
    outliers: frozenset  # ids shown as their own individual flags alongside the collapsed label


def resolve_flag_view(
    selected_ids: frozenset,
    offense_ids: frozenset,
    defense_ids: frozenset,
    all_ids: frozenset,
) -> FlagView:
    """Determines whether the current selection should collapse to one
    "All Players"/"Offense Players"/"Defense Players" flag (+ any outlier
    ids not covered by that group, shown as their own individual flags), or
    just show every selected id as its own flag.

    Priority: all > offense/defense > individual -- a selection that
    happens to equal the full all-players set collapses to "All Players"
    even though it's technically also a superset of offense and defense.
    Empty candidate sets (e.g. a team/timeline combination with no
    resolved offense players at all) never trigger a collapse -- an empty
    selected_ids would otherwise vacuously satisfy "superset of empty set".
    """
    if all_ids and selected_ids == all_ids:
        return FlagView(mode="all", label="All Players", outliers=frozenset())
    if offense_ids and selected_ids >= offense_ids:
        return FlagView(mode="offense", label="Offense Players", outliers=selected_ids - offense_ids)
    if defense_ids and selected_ids >= defense_ids:
        return FlagView(mode="defense", label="Defense Players", outliers=selected_ids - defense_ids)
    return FlagView(mode="individual", label=None, outliers=selected_ids)


def flag_badge_html(label: str) -> str:
    return f'<span style="{FLAG_BADGE_STYLE}">{html.escape(label)}</span>'
