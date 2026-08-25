"""Streamlit widget wiring for the multi-player selector and portrait wall.

Kept separate from app.py (which imports and calls these) so it's testable
in isolation via AppTest without triggering app.py's top-level network
calls (client.get_teams() etc. run immediately on import, since app.py is
a flat script). The pure label-formatting logic these functions call lives
in utils/player_selection.py and utils/player_cards.py.
"""
from __future__ import annotations

import streamlit as st

from utils.player_cards import player_card_html, portrait_wall_html
from utils.player_selection import player_flag_html, player_flag_label
from utils.positions import POSITION_FULL_NAMES, POSITION_GROUPS


def _sync_bulk_checkbox(checkbox_key: str, ids_key: str, candidate_ids: frozenset) -> None:
    if st.session_state[checkbox_key]:
        st.session_state[ids_key] = st.session_state[ids_key] | candidate_ids
    else:
        st.session_state[ids_key] = st.session_state[ids_key] - candidate_ids


def _remove_id(ids_key: str, player_id: int) -> None:
    st.session_state[ids_key] = st.session_state[ids_key] - {player_id}


def _sync_from_multiselect(ids_key: str, ms_key: str) -> None:
    st.session_state[ids_key] = set(st.session_state[ms_key])

def render_player_selection(prefix: str, bio_by_id: dict, candidate_ids_by_position: dict) -> set:
    """Multi-player picker: an "All Players" bulk checkbox, four
    position-group checkboxes (Battery/Infield/Outfield/Non-Fielders) each
    with its own child position checkboxes, removable per-player flags, and
    a lazily-mounted multiselect for adding/removing individual players
    (button-gated rather than an st.expander, since an all-time roster can
    run into the thousands of players -- see macroservice/roster_history.py
    -- and an expander still instantiates its child widgets while collapsed).

    Checking a group checkbox selects every position within it; unchecking
    any one of its child position checkboxes un-checks the group -- both
    directions fall out of re-deriving every checkbox's displayed state
    from the current selection on every render (the same "is the selection
    now a superset of this checkbox's candidate ids" rule used for "All
    Players" below).

    ``candidate_ids_by_position`` maps each position acronym to the ids of
    players holding that position who are active within the caller's
    current timeline range -- both the checkboxes' candidate sets and the
    multiselect's own option list are scoped to this, so moving the
    timeline automatically re-filters which players are selectable.

    Returns the current set of selected player ids.
    """
    ids_key = f"{prefix}_selected_ids"
    if ids_key not in st.session_state:
        st.session_state[ids_key] = set()

    all_ids = frozenset().union(*candidate_ids_by_position.values()) if candidate_ids_by_position else frozenset()
    selected = st.session_state[ids_key]

    all_key = f"{prefix}_all_cb"
    # Superset check (>=), not equality -- matches the group/position rule
    # below and stays correctly checked even if `selected` still holds
    # stale ids that fell out of `all_ids` after a Timeline change.
    st.session_state[all_key] = bool(all_ids) and selected >= all_ids
    st.checkbox("All Players", key=all_key, on_change=_sync_bulk_checkbox, args=(all_key, ids_key, all_ids))

    for group_name, positions in POSITION_GROUPS.items():
        group_ids = frozenset().union(*(candidate_ids_by_position.get(p, frozenset()) for p in positions))
        group_key = f"{prefix}_group_{group_name}_cb"
        st.session_state[group_key] = bool(group_ids) and selected >= group_ids

        cols = st.columns([2] + [2] * len(positions))
        cols[0].checkbox(
            group_name, key=group_key, on_change=_sync_bulk_checkbox, args=(group_key, ids_key, group_ids)
        )
        for col, position in zip(cols[1:], positions):
            pos_ids = candidate_ids_by_position.get(position, frozenset())
            pos_key = f"{prefix}_pos_{position}_cb"
            st.session_state[pos_key] = bool(pos_ids) and selected >= pos_ids
            col.checkbox(
                POSITION_FULL_NAMES[position],
                key=pos_key,
                on_change=_sync_bulk_checkbox,
                args=(pos_key, ids_key, pos_ids),
            )

    selected = st.session_state[ids_key]  # re-read: the checkboxes above may have just changed it
    flag_ids = sorted(selected, key=lambda pid: bio_by_id.get(pid, {}).get("name", ""))
    for player_id in flag_ids:
        bio = bio_by_id.get(player_id, {"name": f"Player {player_id}"})
        badge_col, remove_col = st.columns([6, 1])
        badge_col.markdown(player_flag_html(bio), unsafe_allow_html=True)
        remove_col.button("×", key=f"{prefix}_remove_{player_id}", on_click=_remove_id, args=(ids_key, player_id))

    edit_key = f"{prefix}_edit_open"
    if st.button("Edit individual players", key=f"{prefix}_edit_btn"):
        st.session_state[edit_key] = not st.session_state.get(edit_key, False)

    if st.session_state.get(edit_key):
        ms_key = f"{prefix}_multiselect"
        current = st.session_state[ids_key]
        if ms_key not in st.session_state or set(st.session_state[ms_key]) != current:
            st.session_state[ms_key] = sorted(current)
        options = sorted(all_ids | current)
        st.multiselect(
            "Add or remove individual players",
            options=options,
            format_func=lambda pid: player_flag_label(bio_by_id.get(pid, {"name": f"Player {pid}"})),
            key=ms_key,
            on_change=_sync_from_multiselect,
            args=(ids_key, ms_key),
        )

    return st.session_state[ids_key]


def render_portrait_wall(selected_ids: set, bio_by_id: dict, headshot_url_fn) -> None:
    if not selected_ids:
        st.info("[No Player Selected]")
        return

    ordered = sorted(selected_ids, key=lambda pid: bio_by_id.get(pid, {}).get("name", ""))
    cards = [
        player_card_html(
            player_flag_label(bio_by_id.get(pid, {"name": f"Player {pid}"})),
            headshot_url_fn(pid),
        )
        for pid in ordered
    ]
    with st.container(height=340, border=True):
        st.markdown(portrait_wall_html(cards), unsafe_allow_html=True)
