"""Pure Plotly rendering of already-computed series and trajectory payloads.

No model fitting happens here -- trajectories arrive pre-fit, and the
multi-metric season chart plots raw yearly actuals. This module only draws.
"""
from __future__ import annotations

import plotly.graph_objects as go

from utils.filters import is_rate_metric

TREND_COLOR = "#FF6B35"
CI_FILL_COLOR = "rgba(255, 107, 53, 0.15)"

# Assigned in checkbox order so a given metric keeps its color as others are
# toggled on and off.
METRIC_PALETTE = [
    "#1F77B4", "#D62728", "#2CA02C", "#FF7F0E",
    "#9467BD", "#8C564B", "#17BECF", "#E377C2",
]


def color_for_metric_index(index: int) -> str:
    return METRIC_PALETTE[index % len(METRIC_PALETTE)]


def _translucent(hex_color: str, alpha: float = 0.15) -> str:
    """Hex to rgba() -- Plotly's color validator rejects 8-digit hex (#RRGGBBAA)."""
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r}, {g}, {b}, {alpha})"


def build_multi_metric_figure(
    series_by_metric: dict[str, dict],
    acronym_by_metric: dict[str, str],
    reveal_upto: int | None = None,
    title: str = "Season Trend",
) -> go.Figure:
    """One line per selected metric across seasons, legend labelled by acronym.

    ``reveal_upto`` truncates every series to its first N points, which is
    how the left-to-right "snake" reveal is animated: the caller re-renders
    this figure with a growing N. ``None`` draws the complete series.

    Rate stats (AVG/OPS/ERA/...) and counting stats (HR/RBI/K/...) are split
    across two y-axes -- on a shared axis the rate lines would collapse onto
    the baseline next to counts in the hundreds.
    """
    fig = go.Figure()
    has_rate = any(is_rate_metric(key) for key in series_by_metric)
    has_count = any(not is_rate_metric(key) for key in series_by_metric)

    for index, (metric_key, series) in enumerate(series_by_metric.items()):
        years = series["years"]
        values = series["values"]
        if reveal_upto is not None:
            years = years[:reveal_upto]
            values = values[:reveal_upto]

        acronym = acronym_by_metric.get(metric_key, metric_key)
        color = color_for_metric_index(index)
        on_rate_axis = is_rate_metric(metric_key)
        fig.add_trace(
            go.Scatter(
                x=years,
                y=values,
                mode="lines+markers",
                name=acronym,
                line={"color": color, "width": 2},
                marker={"color": color, "size": 7},
                yaxis="y" if on_rate_axis or not has_rate else "y2",
                hovertemplate=f"%{{x}}<br>{acronym}: %{{y}}<extra></extra>",
            )
        )

    fig.update_layout(
        title=title,
        xaxis_title="Season",
        xaxis={"dtick": 1},
        yaxis_title="Rate" if has_rate else "Total",
        template="plotly_dark",
        hovermode="x unified",
        margin={"t": 56, "b": 40, "l": 48, "r": 48},
    )
    if has_rate and has_count:
        fig.update_layout(yaxis2={"title": "Total", "overlaying": "y", "side": "right"})
    return fig


def build_forecast_figure(
    forecast_by_metric: dict[str, dict],
    acronym_by_metric: dict[str, str],
    reveal_upto: int | None = None,
    title: str = "Forecast",
) -> go.Figure:
    """Per selected metric: a shaded 90% CI band, a forecast trend line
    spanning [train_end, forecast_end], and actual markers wherever real
    ground truth exists in that same window (``None`` entries in
    ``forecast_by_metric[key]["actual"]`` are skipped, not plotted as 0).

    ``reveal_upto`` truncates every series to its first N points for the
    left-to-right snake reveal, same convention as build_multi_metric_figure.
    """
    fig = go.Figure()
    has_rate = any(is_rate_metric(key) for key in forecast_by_metric)
    has_count = any(not is_rate_metric(key) for key in forecast_by_metric)

    for index, (metric_key, payload) in enumerate(forecast_by_metric.items()):
        years = payload["years"]
        forecast = payload["forecast"]
        ci_lower = payload["ci_lower"]
        ci_upper = payload["ci_upper"]
        actual = payload["actual"]
        if reveal_upto is not None:
            years = years[:reveal_upto]
            forecast = forecast[:reveal_upto]
            ci_lower = ci_lower[:reveal_upto]
            ci_upper = ci_upper[:reveal_upto]
            actual = actual[:reveal_upto]

        acronym = acronym_by_metric.get(metric_key, metric_key)
        color = color_for_metric_index(index)
        axis = "y" if is_rate_metric(metric_key) or not has_rate else "y2"

        if years:
            fig.add_trace(
                go.Scatter(
                    x=years + years[::-1],
                    y=ci_upper + ci_lower[::-1],
                    fill="toself", fillcolor=_translucent(color), line={"width": 0},
                    yaxis=axis, name=f"{acronym} 90% CI", hoverinfo="skip",
                )
            )
        fig.add_trace(
            go.Scatter(
                x=years, y=forecast, mode="lines", name=f"{acronym} forecast",
                line={"color": color, "dash": "dot", "width": 2},
                yaxis=axis, hoverinfo="skip",
            )
        )

        actual_years = [year for year, value in zip(years, actual) if value is not None]
        actual_values = [value for value in actual if value is not None]
        if actual_years:
            fig.add_trace(
                go.Scatter(
                    x=actual_years, y=actual_values, mode="markers", name=f"{acronym} actual",
                    marker={"color": color, "size": 9, "symbol": "diamond", "line": {"width": 1, "color": "#333"}},
                    yaxis=axis, hovertemplate=f"%{{x}}<br>{acronym}: %{{y}}<extra></extra>",
                )
            )

    fig.update_layout(
        title=title,
        xaxis_title="Season",
        xaxis={"dtick": 1},
        yaxis_title="Rate" if has_rate else "Total",
        template="plotly_dark",
        hovermode="x unified",
        margin={"t": 56, "b": 40, "l": 48, "r": 48},
    )
    if has_rate and has_count:
        fig.update_layout(yaxis2={"title": "Total", "overlaying": "y", "side": "right"})
    return fig


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
            name="90% CI", hoverinfo="skip",
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
        template="plotly_dark",
        hovermode="x unified",
        margin={"t": 56, "b": 40, "l": 48, "r": 24},
    )
    return fig
