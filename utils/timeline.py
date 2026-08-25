"""Year-range timeline controls for the dashboard.

Streamlit has no native multi-handle slider with custom collision physics,
so these are a pragmatic native approximation: a two-value st.slider
(which already can't be dragged past itself) mirrored to number inputs via
st.session_state, plus a single "pushed" scrubber whose lower bound tracks
another timeline's end year every rerun. There is no live drag-collision
feel (a handle just clamps at contact rather than pushing its neighbor) --
a from-scratch custom component would be needed for that, and is
explicitly deferred.
"""
from __future__ import annotations

import streamlit as st


def year_range_control(key_prefix: str, min_year: int, max_year: int, label: str = "Year range") -> tuple[int, int]:
    """Two-handle year range slider, mirrored to two number inputs.

    Same-year overlap (both handles on one year) is allowed -- the slider
    supports it natively, and the number inputs are the primary way to
    tell the two apart when the slider's handles visually coincide.
    Typing an out-of-range or inverted year into a number input reverts to
    the last valid value rather than applying it.
    """
    slider_key = f"{key_prefix}_range_slider"
    start_key = f"{key_prefix}_range_start"
    end_key = f"{key_prefix}_range_end"

    if slider_key not in st.session_state:
        st.session_state[slider_key] = (min_year, max_year)
        st.session_state[start_key] = min_year
        st.session_state[end_key] = max_year

    def _on_slider_change() -> None:
        start, end = st.session_state[slider_key]
        st.session_state[start_key] = start
        st.session_state[end_key] = end

    def _on_start_input_change() -> None:
        start = st.session_state[start_key]
        end = st.session_state[end_key]
        if not (min_year <= start <= end):
            st.session_state[start_key] = st.session_state[slider_key][0]
            return
        st.session_state[slider_key] = (start, end)

    def _on_end_input_change() -> None:
        start = st.session_state[start_key]
        end = st.session_state[end_key]
        if not (start <= end <= max_year):
            st.session_state[end_key] = st.session_state[slider_key][1]
            return
        st.session_state[slider_key] = (start, end)

    st.slider(label, min_value=min_year, max_value=max_year, key=slider_key, on_change=_on_slider_change)

    start_col, end_col = st.columns(2)
    start_col.number_input(
        "Start year", min_value=min_year, max_value=max_year, key=start_key, on_change=_on_start_input_change
    )
    end_col.number_input(
        "End year", min_value=min_year, max_value=max_year, key=end_key, on_change=_on_end_input_change
    )

    return st.session_state[slider_key]


def pushed_year_control(
    key_prefix: str, min_year_source: int, max_year: int, slider_floor_year: int, label: str = "Forecast horizon"
) -> int:
    """Single-value year scrubber that tracks a floor of ``min_year_source``:
    pushed forward if that source moves past it, but never pushed back
    (this function never writes to whatever produced ``min_year_source``).

    ``slider_floor_year`` is a fixed, session-stable lower bound for the
    underlying widgets (e.g. the dashboard's earliest supported season) --
    deliberately NOT ``min_year_source`` itself. Streamlit resets a keyed
    slider/number_input's value to its own min_value whenever that
    min_value changes between reruns, even when the stored value is
    already within the new range (confirmed via direct testing); passing
    a live-changing min_year_source as min_value would spuriously reset
    this scrubber on every rerun where the source moves, including moving
    backward, which would silently violate "never pushed back". The real
    ``min_year_source`` floor is enforced manually instead, below.

    ``min_year_source`` can exceed ``max_year`` (e.g. the training range's
    end year is later than this control's fixed ceiling) -- that's clamped
    to ``max_year``, pinning this scrubber at the ceiling. That collapses
    the forecast window to zero width, which is exactly the "no forecast"
    edge case the caller is expected to already handle when the two
    scrubbers coincide.
    """
    value_key = f"{key_prefix}_pushed_value"
    input_key = f"{key_prefix}_pushed_input"
    effective_min = min(min_year_source, max_year)

    if value_key not in st.session_state:
        st.session_state[value_key] = effective_min
        st.session_state[input_key] = effective_min

    if st.session_state[value_key] < effective_min:
        st.session_state[value_key] = effective_min
        st.session_state[input_key] = effective_min

    def _on_slider_change() -> None:
        value = st.session_state[value_key]
        if value < effective_min:
            st.session_state[value_key] = effective_min
            value = effective_min
        st.session_state[input_key] = value

    def _on_input_change() -> None:
        value = st.session_state[input_key]
        if not (effective_min <= value <= max_year):
            st.session_state[input_key] = st.session_state[value_key]
            return
        st.session_state[value_key] = value

    st.slider(label, min_value=slider_floor_year, max_value=max_year, key=value_key, on_change=_on_slider_change)
    st.number_input(
        "Forecast year", min_value=slider_floor_year, max_value=max_year, key=input_key, on_change=_on_input_change
    )

    return st.session_state[value_key]
