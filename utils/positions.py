"""Position taxonomy shared by player selection and portrait cards.

Group membership mirrors the four row categories in the player selector
(see utils/selection_widgets.py) -- each group is a plain row label, with
one checkbox per position underneath it. Those checkboxes use the full
position name; the multiselect and portrait cards use the acronym.
"""
from __future__ import annotations

POSITION_GROUPS: dict[str, list[str]] = {
    "Battery": ["P", "C"],
    "Infield": ["1B", "2B", "3B", "SS"],
    "Outfield": ["LF", "CF", "RF"],
    "Non-Fielders": ["DH", "TWP", "PH", "PR", "UTL"],
}

POSITION_FULL_NAMES: dict[str, str] = {
    "P": "Pitcher",
    "C": "Catcher",
    "1B": "First Base",
    "2B": "Second Base",
    "3B": "Third Base",
    "SS": "Shortstop",
    "LF": "Left Field",
    "CF": "Center Field",
    "RF": "Right Field",
    "DH": "Designated Hitter",
    "TWP": "Two-Way Player",
    "PH": "Pinch Hitter",
    "PR": "Pinch Runner",
    "UTL": "Utility",
}

GROUP_FOR_POSITION: dict[str, str] = {
    position: group for group, positions in POSITION_GROUPS.items() for position in positions
}

ALL_POSITIONS: frozenset[str] = frozenset(GROUP_FOR_POSITION)


def format_position_tag(positions: list[str]) -> str:
    """"[SS]" for a single position, "[SS, 2B]" for a multi-position player."""
    return f"[{', '.join(positions)}]" if positions else "[?]"
