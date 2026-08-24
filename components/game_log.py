"""Per-game box score table for the selected player."""
from __future__ import annotations

import pandas as pd
import panel as pn

_COLUMN_TITLES = {
    "date": "Date", "opponent": "Opponent",
    "atBats": "AB", "hits": "H", "homeRuns": "HR", "rbi": "RBI",
    "baseOnBalls": "BB", "strikeOuts": "K", "avg": "AVG",
    "inningsPitched": "IP", "earnedRuns": "ER", "era": "ERA",
}


def build_game_log(df: pd.DataFrame, columns: list[str]) -> pn.widgets.Tabulator:
    display_df = df[columns].copy()
    if "date" in display_df.columns:
        display_df["date"] = pd.to_datetime(display_df["date"]).dt.strftime("%Y-%m-%d")

    return pn.widgets.Tabulator(
        display_df,
        titles={col: _COLUMN_TITLES.get(col, col) for col in columns},
        disabled=True,
        show_index=False,
        page_size=15,
        pagination="local",
        sizing_mode="stretch_width",
    )
