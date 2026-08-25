"""Pure Plotly rendering of a pre-fit trajectory payload from the data service.

No model fitting happens here -- the ensemble was already fit server-side.
This only draws it: actual values (train vs. holdout markers), the blended
trend line, a shaded 95% CI band, and a vertical train/holdout cutoff line.
"""
from __future__ import annotations

import plotly.graph_objects as go

TREND_COLOR = "#FF6B35"
CI_FILL_COLOR = "rgba(255, 107, 53, 0.15)"


def build_trajectory_figure(payload: dict, series_color: str) -> go.Figure:
    x_labels = payload["x_labels"]
    y = payload["y_actual"]
    split = payload["split_index"]
    n = len(y)
    metric_label = payload["metric_label"]
    hover_extra = payload.get("hover_extra")
    hover_extra_label = payload.get("hover_extra_label", "")

    fig = go.Figure()

    if 0 < split < n:
        fig.add_vline(
            x=x_labels[split], line_dash="dash", line_color="#999",
            annotation_text="train / holdout", annotation_position="top",
        )

    fig.add_trace(
        go.Scatter(
            x=x_labels + x_labels[::-1],
            y=payload["ci_upper"] + payload["ci_lower"][::-1],
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
            x=x_labels, y=payload["y_pred"], mode="lines", name=f"{metric_label} trend (ensemble)",
            line={"color": TREND_COLOR, "dash": "dot", "width": 2},
            hoverinfo="skip",
        )
    )

    subtitle = ""
    if payload["holdout_r2"] is not None:
        subtitle = f" — holdout R²={payload['holdout_r2']:.3f}, RMSE={payload['holdout_rmse']:.3f}"

    fig.update_layout(
        title=f"{metric_label} Trajectory{subtitle}",
        xaxis_title=payload["x_title"],
        yaxis_title=metric_label,
        template="plotly_white",
        hovermode="x unified",
        margin={"t": 56, "b": 40, "l": 48, "r": 24},
    )
    return fig
