"""Streamlit widget wiring for the multi-player selector and portrait wall.

Kept separate from app.py (which imports and calls these) so it's testable
in isolation via AppTest without triggering app.py's top-level network
calls (client.get_teams() etc. run immediately on import, since app.py is
a flat script). The pure collapse-detection/HTML-building logic these
functions call lives in utils/player_selection.py and utils/player_cards.py.
"""
from __future__ import annotations

import streamlit as st

from utils.player_cards import player_card_html, portrait_wall_html
from utils.player_selection import flag_badge_html, resolve_flag_view


def _sync_bulk_checkbox(checkbox_key: str, ids_key: str, candidate_ids: frozenset) -> None:
    if st.session_state[checkbox_key]:
        st.session_state[ids_key] = st.session_state[ids_key] | candidate_ids
    else:
        st.session_state[ids_key] = st.session_state[ids_key] - candidate_ids


def _remove_id(ids_key: str, player_id: int) -> None:
    st.session_state[ids_key] = st.session_state[ids_key] - {player_id}


def _clear_group(ids_key: str, checkbox_key: str, candidate_ids: frozenset) -> None:
    st.session_state[ids_key] = st.session_state[ids_key] - candidate_ids
    st.session_state[checkbox_key] = False


def _sync_from_multiselect(ids_key: str, ms_key: str) -> None:
    st.session_state[ids_key] = set(st.session_state[ms_key])


def render_player_selection(
    prefix: str,
    bio_by_id: dict,
    offense_ids: frozenset,
    defense_ids: frozenset,
    all_ids: frozenset,
    browsable_ids: frozenset,
) -> set:
    """Multi-select player picker: bulk Offense/Defense/All-Players
    checkboxes, removable flags (collapsed to one group flag when a bulk
    group is fully selected -- see utils.player_selection.resolve_flag_view),
    and a lazily-mounted multiselect for adding/removing individual players
    (button-gated rather than an st.expander, since an all-time roster can
    run into the thousands of players -- see macroservice/roster_history.py
    -- and an expander still instantiates its child widgets while collapsed).

    ``browsable_ids`` scopes the multiselect's own option list (e.g. the
    Season dropdown's single-season roster, "Season selection filters the
    roster") -- distinct from ``bio_by_id``, which covers the full all-time
    roster and is used for every name/years lookup, since a bulk-selected
    or previously-picked id can be outside the current browsable set.

    Returns the current set of selected player ids.
    """
    ids_key = f"{prefix}_selected_ids"
    if ids_key not in st.session_state:
        st.session_state[ids_key] = set()

    offense_key, defense_key, all_key = f"{prefix}_offense_cb", f"{prefix}_defense_cb", f"{prefix}_all_cb"
    selected = st.session_state[ids_key]
    # Keep the bulk checkboxes' displayed state honest even when the
    # underlying selection changed some other way (e.g. removing one
    # offense player's individual flag should auto-uncheck "Offense").
    st.session_state[offense_key] = bool(offense_ids) and selected >= offense_ids
    st.session_state[defense_key] = bool(defense_ids) and selected >= defense_ids
    st.session_state[all_key] = bool(all_ids) and selected == all_ids

    bulk_cols = st.columns(3)
    bulk_cols[0].checkbox(
        "Offense", key=offense_key, on_change=_sync_bulk_checkbox, args=(offense_key, ids_key, offense_ids)
    )
    bulk_cols[1].checkbox(
        "Defense", key=defense_key, on_change=_sync_bulk_checkbox, args=(defense_key, ids_key, defense_ids)
    )
    bulk_cols[2].checkbox("All Players", key=all_key, on_change=_sync_bulk_checkbox, args=(all_key, ids_key, all_ids))

    selected = st.session_state[ids_key]  # re-read: a checkbox callback above may have just changed it
    view = resolve_flag_view(frozenset(selected), offense_ids, defense_ids, all_ids)

    if view.mode == "individual":
        flag_ids = sorted(view.outliers, key=lambda pid: bio_by_id.get(pid, {}).get("name", ""))
    else:
        group_checkbox_key = {"offense": offense_key, "defense": defense_key, "all": all_key}[view.mode]
        group_candidate_ids = {"offense": offense_ids, "defense": defense_ids, "all": all_ids}[view.mode]
        badge_col, remove_col = st.columns([6, 1])
        badge_col.markdown(flag_badge_html(view.label), unsafe_allow_html=True)
        remove_col.button(
            "×",
            key=f"{prefix}_remove_group",
            on_click=_clear_group,
            args=(ids_key, group_checkbox_key, group_candidate_ids),
        )
        flag_ids = sorted(view.outliers, key=lambda pid: bio_by_id.get(pid, {}).get("name", ""))

    for player_id in flag_ids:
        name = bio_by_id.get(player_id, {}).get("name", f"Player {player_id}")
        badge_col, remove_col = st.columns([6, 1])
        badge_col.markdown(flag_badge_html(name), unsafe_allow_html=True)
        remove_col.button("×", key=f"{prefix}_remove_{player_id}", on_click=_remove_id, args=(ids_key, player_id))

    edit_key = f"{prefix}_edit_open"
    if st.button("Edit individual players", key=f"{prefix}_edit_btn"):
        st.session_state[edit_key] = not st.session_state.get(edit_key, False)

    if st.session_state.get(edit_key):
        ms_key = f"{prefix}_multiselect"
        current = st.session_state[ids_key]
        if ms_key not in st.session_state or set(st.session_state[ms_key]) != current:
            st.session_state[ms_key] = sorted(current)
        options = sorted(browsable_ids | current)
        st.multiselect(
            "Add or remove individual players",
            options=options,
            format_func=lambda pid: (
                f"{bio_by_id.get(pid, {}).get('name', f'Player {pid}')}"
                f" ({bio_by_id.get(pid, {}).get('active_years_label', '')})"
            ),
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
            bio_by_id.get(pid, {}).get("name", f"Player {pid}"),
            bio_by_id.get(pid, {}).get("active_years_label", ""),
            headshot_url_fn(pid),
            bio_by_id.get(pid, {}).get("is_pitcher", False),
        )
        for pid in ordered
    ]
    with st.container(height=340, border=True):
        st.markdown(portrait_wall_html(cards), unsafe_allow_html=True)
