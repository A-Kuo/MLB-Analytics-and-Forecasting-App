"""Stat formatting helpers matching conventional baseball notation."""
from __future__ import annotations

# Rate stats conventionally printed without the leading zero, e.g. ".287".
_LEADING_ZERO_DROPPED = {"avg", "obp", "slg", "ops"}
# Rate stats conventionally printed to two decimal places, e.g. "3.45".
_TWO_DECIMAL = {"era", "whip", "strikeoutsPer9Inn", "walksPer9Inn", "fip"}


def format_stat(value, key: str) -> str:
    if value is None or value == "":
        return "—"

    if key in _LEADING_ZERO_DROPPED:
        try:
            text = f"{float(value):.3f}"
        except (TypeError, ValueError):
            return str(value)
        return text[1:] if text.startswith("0.") else text

    if key in _TWO_DECIMAL:
        try:
            return f"{float(value):.2f}"
        except (TypeError, ValueError):
            return str(value)

    return str(value)
