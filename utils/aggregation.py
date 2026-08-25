"""Pure aggregation logic for combining multiple players' season series
into one number (Aggregate KPI) or one combined series (Performance Trend/
Forecast) -- sum for counting stats, mean for rate stats, per Austin's
explicit choice of the simpler (not pooled-totals-recomputed) aggregation
rule. This extends uniformly across both dimensions being combined
(players and years): every (player, year) data point in range is treated
as one equally-weighted sample, whether the selection is one player, many,
or a full team, and whether the timeline spans one year or many.

No Streamlit/network dependency -- takes already-fetched series data
(the {"years": [...], "values": [...]} shape every macroservice season
series function already returns).
"""
from __future__ import annotations


def aggregate_series(series_by_player: dict[int, dict], is_rate: bool) -> dict:
    """Combines per-player series into ONE series: for each year that
    appears in at least one player's series, sum (counting stats) or mean
    (rate stats) that year's values across whichever players have data for
    that year. A player with no data in a given year (outside their active
    span, Statcast unavailable that year, etc.) simply doesn't contribute
    to that year's point, rather than blocking the whole year.
    """
    values_by_year: dict[int, list[float]] = {}
    for series in series_by_player.values():
        for year, value in zip(series["years"], series["values"]):
            values_by_year.setdefault(year, []).append(value)

    years = sorted(values_by_year)
    if is_rate:
        combined = [sum(values_by_year[year]) / len(values_by_year[year]) for year in years]
    else:
        combined = [sum(values_by_year[year]) for year in years]
    return {"years": years, "values": combined}


def aggregate_scalar(series_by_player: dict[int, dict], is_rate: bool) -> float | None:
    """Single aggregate number across every (player, year) point in range --
    for Aggregate KPI cards, which show one value per metric for the
    current selection + timeline range, not a per-year trend.
    """
    all_values = [value for series in series_by_player.values() for value in series["values"]]
    if not all_values:
        return None
    return (sum(all_values) / len(all_values)) if is_rate else sum(all_values)
