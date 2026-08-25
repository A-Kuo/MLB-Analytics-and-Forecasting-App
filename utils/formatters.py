"""Stat formatting helpers matching conventional baseball notation."""
from __future__ import annotations

# Rate stats conventionally printed without the leading zero, e.g. ".287".
# xba is on the same batting-average scale, so it joins this bucket rather
# than the percent bucket below.
_LEADING_ZERO_DROPPED = {"avg", "obp", "slg", "ops", "xba"}
# Rate stats conventionally printed to two decimal places, e.g. "3.45".
_TWO_DECIMAL = {"era", "whip", "strikeoutsPer9Inn", "walksPer9Inn", "fip"}
# Statcast fractions (0-1) printed as a percentage, e.g. "34.2%".
_PERCENT = {"hardHitPct", "barrelPct", "cswPct", "whiffPct", "chasePct"}
# Statcast velocities, e.g. "94.3 mph".
_MPH = {"avgExitVelocity", "avgVelocity"}


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

    if key in _PERCENT:
        try:
            return f"{float(value) * 100:.1f}%"
        except (TypeError, ValueError):
            return str(value)

    if key in _MPH:
        try:
            return f"{float(value):.1f} mph"
        except (TypeError, ValueError):
            return str(value)

    return str(value)


def format_active_years(ranges: list[tuple[int, int | None]]) -> str:
    """"2015–2020" for one span, "2015–2017, 2019–present" for several --
    a player who left a team's roster and later returned. Today's roster
    data source only ever produces a single span (see
    macroservice/roster_history.py), but callers format through this
    either way so a future multi-span data source needs no display changes.
    """
    if not ranges:
        return ""
    return ", ".join(f"{start}–{'present' if end is None else end}" for start, end in ranges)
