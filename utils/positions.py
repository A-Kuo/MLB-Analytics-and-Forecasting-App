"""Position taxonomy shared by player selection, portrait cards, and flags.

Group membership mirrors the four checkbox categories in the player
selector: checking a group checkbox selects every position within it;
unchecking any one position checkbox un-checks its parent group (see
utils/selection_widgets.py). Checkbox labels use the full position name;
flags and portrait cards use the acronym.
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

# One color per group, used to tint selected-player flags -- the portrait
# wall deliberately drops color coding (see utils/player_cards.py) since
# Austin asked for the wall to stay plain, but flags keep it as a quick
# at-a-glance position cue.
GROUP_COLORS: dict[str, str] = {
    "Battery": "#C77B00",
    "Infield": "#1F7A3D",
    "Outfield": "#1F4E9C",
    "Non-Fielders": "#6B3FA0",
}
DEFAULT_COLOR = "#555555"


def color_for_positions(positions: list[str]) -> str:
    """Color for a (possibly multi-position) player -- keyed off the first
    listed position, which is treated as primary throughout.
    """
    if not positions:
        return DEFAULT_COLOR
    group = GROUP_FOR_POSITION.get(positions[0])
    return GROUP_COLORS.get(group, DEFAULT_COLOR)


def format_position_tag(positions: list[str]) -> str:
    """"[SS]" for a single position, "[SS, 2B]" for a multi-position player."""
    return f"[{', '.join(positions)}]" if positions else "[?]"
