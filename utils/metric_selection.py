"""Shared button-gated compute state machine for metric checkbox panels.

Performance Trend, Forecast, and Aggregate KPI all follow the same shape:
nothing computes until a button is pressed; unchecking a metric drops it
from the display immediately without recomputing; checking a metric that
was never part of the last press clears the display until the button is
pressed again (never show a stale or partial result for the current
checkbox state). Two decoupled helpers, since "did the subject change"
(team/players/group) and "handle a button press against the checked
metrics" are separate concerns that happen to always appear together here.
"""
from __future__ import annotations

from contextlib import nullcontext
from typing import Callable

import streamlit as st


def reset_on_subject_change(subject_state_key: str, subject_key, computed_defaults: dict) -> bool:
    """Clears every key in ``computed_defaults`` to its given default the
    moment ``subject_key`` (e.g. team + selected players + group) differs
    from what was stored under ``subject_state_key`` on a prior run --
    otherwise a stale computed result for the previous subject would keep
    showing until the button happens to be pressed again. Returns whether a
    reset happened.
    """
    changed = st.session_state.get(subject_state_key) != subject_key
    if changed:
        st.session_state[subject_state_key] = subject_key
        for key, default in computed_defaults.items():
            st.session_state[key] = default
    return changed


def metric_button_state_machine(
    pressed: bool,
    selected_metrics: list[tuple[str, str]],
    computed_state_key: str,
    acronyms_state_key: str,
    compute_fn: Callable[[str], object],
    spinner_message: str | None = None,
) -> dict:
    """Runs ``compute_fn(key)`` for each selected metric only when
    ``pressed`` is True, caches the result in ``st.session_state`` under
    ``computed_state_key``, and returns the subset of that cache matching
    the currently checked metrics. Unchecking a metric simply drops it from
    the returned dict (no recompute); checking a metric that isn't in the
    cache clears the whole cache until the button is pressed again, so a
    partial/stale result is never shown for the current checkbox state.
    """
    current_keys = {key for key, _ in selected_metrics}
    computed = st.session_state.get(computed_state_key, {})

    if pressed and selected_metrics:
        with st.spinner(spinner_message) if spinner_message else nullcontext():
            computed = {key: compute_fn(key) for key, _ in selected_metrics}
        st.session_state[computed_state_key] = computed
        st.session_state[acronyms_state_key] = dict(selected_metrics)
    elif current_keys - computed.keys():
        computed = {}
        st.session_state[computed_state_key] = {}

    return {key: computed[key] for key in current_keys if key in computed}
