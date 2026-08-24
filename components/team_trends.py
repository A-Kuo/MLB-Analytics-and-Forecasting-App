"""Team-level rolling offense/defense trajectory charts (10-game rolling runs)."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from components.line_chart import build_trajectory_chart
from utils.features import build_team_rolling_frame

DEFENSE_COLOR = "#C41E3A"


def build_team_offense_chart(schedule_df: pd.DataFrame, team_color: str) -> go.Figure:
    frame = build_team_rolling_frame(schedule_df)
    return build_trajectory_chart(
        x_labels=frame["date"],
        y=frame["rolling_runs_for"].tolist(),
        X_features=frame[["game_num"]].to_numpy(),
        metric_label="Rolling Runs Scored (10-game)",
        series_color=team_color,
        hover_extra=frame["opponent"].tolist(),
        hover_extra_label="Opponent",
    )


def build_team_defense_chart(schedule_df: pd.DataFrame, team_color: str) -> go.Figure:
    frame = build_team_rolling_frame(schedule_df)
    return build_trajectory_chart(
        x_labels=frame["date"],
        y=frame["rolling_runs_against"].tolist(),
        X_features=frame[["game_num"]].to_numpy(),
        metric_label="Rolling Runs Allowed (10-game)",
        series_color=DEFENSE_COLOR,
        hover_extra=frame["opponent"].tolist(),
        hover_extra_label="Opponent",
    )
