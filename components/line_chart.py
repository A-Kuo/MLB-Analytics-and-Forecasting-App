"""Plotly trajectory charts: actual values, blended ensemble trend, 95% CI
band, distinct train/holdout marker styling, and a chronological cutoff line.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from models.regression import fit_trajectory_ensemble
from utils.features import CSW_ROLLING_WINDOW, HITTER_FEATURE_COLUMNS, HITTER_ROLLING_WINDOW, PITCHER_FEATURE_COLUMNS

TREND_COLOR = "#FF6B35"
CI_FILL_COLOR = "rgba(255, 107, 53, 0.15)"
RATE_STAT_BOUNDS = (0.0, 1.5)


def build_trajectory_chart(
    x_labels,
    y: list[float],
    X_features: np.ndarray,
    metric_label: str,
    series_color: str,
    hover_extra: list[str] | None = None,
    hover_extra_label: str = "",
    x_title: str = "Game Date",
    bounds: tuple[float, float] | None = None,
) -> go.Figure:
    x_labels = list(x_labels)
    y = list(y)
    fit = fit_trajectory_ensemble(X_features, np.asarray(y, dtype=float), bounds=bounds)
    n = len(y)
    split = fit.split_index

    fig = go.Figure()

    if 0 < split < n:
        fig.add_vline(
            x=x_labels[split], line_dash="dash", line_color="#999",
            annotation_text="train / holdout", annotation_position="top",
        )

    fig.add_trace(
        go.Scatter(
            x=x_labels + x_labels[::-1],
            y=list(fit.ci_upper) + list(fit.ci_lower)[::-1],
            fill="toself", fillcolor=CI_FILL_COLOR, line={"width": 0},
            name="95% CI", hoverinfo="skip",
        )
    )

    hover_label = f"{hover_extra_label}: %{{customdata}}<br>" if hover_extra else ""
    hovertemplate = "%{x}<br>" + hover_label + f"{metric_label}: " + "%{y:.3f}<extra></extra>"

    fig.add_trace(
        go.Scatter(
            x=x_labels[:split], y=y[:split], mode="markers", name="Train (actual)",
            marker={"color": series_color, "symbol": "circle", "size": 7},
            customdata=hover_extra[:split] if hover_extra else None,
            hovertemplate=hovertemplate,
        )
    )
    if split < n:
        fig.add_trace(
            go.Scatter(
                x=x_labels[split:], y=y[split:], mode="markers", name="Holdout (actual)",
                marker={"color": series_color, "symbol": "diamond", "size": 9, "line": {"width": 1, "color": "#333"}},
                customdata=hover_extra[split:] if hover_extra else None,
                hovertemplate=hovertemplate,
            )
        )

    fig.add_trace(
        go.Scatter(
            x=x_labels, y=fit.y_pred_all, mode="lines", name=f"{metric_label} trend (ensemble)",
            line={"color": TREND_COLOR, "dash": "dot", "width": 2},
            hoverinfo="skip",
        )
    )

    subtitle = ""
    if fit.holdout_r2 is not None:
        subtitle = f" — holdout R²={fit.holdout_r2:.3f}, RMSE={fit.holdout_rmse:.3f}"

    fig.update_layout(
        title=f"{metric_label} Trajectory{subtitle}",
        xaxis_title=x_title,
        yaxis_title=metric_label,
        template="plotly_white",
        hovermode="x unified",
        margin={"t": 56, "b": 40, "l": 48, "r": 24},
    )
    return fig


def build_hitter_chart(frame: pd.DataFrame, metric_key: str, metric_label: str, team_color: str) -> go.Figure:
    valid = frame.dropna(subset=["rolling_metric"]).reset_index(drop=True)
    bounds = RATE_STAT_BOUNDS if metric_key in ("avg", "obp", "slg", "ops") else None
    return build_trajectory_chart(
        x_labels=valid["date"],
        y=valid["rolling_metric"].tolist(),
        X_features=valid[HITTER_FEATURE_COLUMNS].to_numpy(),
        metric_label=f"{metric_label} (rolling {HITTER_ROLLING_WINDOW}-game)",
        series_color=team_color,
        hover_extra=valid["opponent"].tolist(),
        hover_extra_label="Opponent",
        bounds=bounds,
    )


def build_pitcher_csw_chart(frame: pd.DataFrame, team_color: str) -> go.Figure:
    return build_trajectory_chart(
        x_labels=frame["pitch_index"],
        y=frame["rolling_csw"].tolist(),
        X_features=frame[PITCHER_FEATURE_COLUMNS].to_numpy(),
        metric_label=f"CSW% (rolling {CSW_ROLLING_WINDOW}-pitch)",
        series_color=team_color,
        x_title="Pitch Index (season-chronological)",
        bounds=(0.0, 1.0),
    )


def build_pitcher_legacy_chart(df: pd.DataFrame, metric_key: str, metric_label: str, team_color: str) -> go.Figure:
    """Appearance-level fallback for when Statcast pitch data is unavailable."""
    valid = df.dropna(subset=[metric_key]).reset_index(drop=True)
    X = np.arange(len(valid)).reshape(-1, 1)
    return build_trajectory_chart(
        x_labels=valid["date"],
        y=valid[metric_key].astype(float).tolist(),
        X_features=X,
        metric_label=metric_label,
        series_color=team_color,
        hover_extra=valid["opponent"].tolist(),
        hover_extra_label="Opponent",
    )
