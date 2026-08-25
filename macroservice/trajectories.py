"""Pre-fits the SVR/Huber/GaussianProcess trajectory ensemble and returns a
JSON-ready payload, so consumers (the Streamlit dashboard) only ever render
a trajectory -- they never fit a model themselves.

Each public function is cached: repeated requests for the same
player/season/metric combination (e.g. a Streamlit rerun triggered by an
unrelated widget) reuse the last fit instead of re-running scikit-learn.
"""
from __future__ import annotations

import numpy as np

from macroservice import players, statcast, teams
from macroservice.caching import cached
from macroservice.features import (
    CSW_ROLLING_WINDOW,
    HITTER_FEATURE_COLUMNS,
    HITTER_ROLLING_WINDOW,
    PITCHER_FEATURE_COLUMNS,
    build_hitter_feature_frame,
    build_pitcher_csw_frame,
    build_team_rolling_frame,
)
from macroservice.regression import fit_and_forecast, fit_trajectory_ensemble
from macroservice.transform import batted_balls_dataframe, game_log_dataframe, pitches_dataframe, schedule_dataframe
from utils.filters import metrics_for_group

TRAJECTORY_TTL_SECONDS = 5 * 60
RATE_STAT_BOUNDS = (0.0, 1.5)


def _payload(
    x_labels: list,
    y: list[float],
    X: np.ndarray,
    metric_label: str,
    x_title: str,
    hover_extra: list[str] | None = None,
    hover_extra_label: str = "",
    bounds: tuple[float, float] | None = None,
) -> dict:
    fit = fit_trajectory_ensemble(np.asarray(X, dtype=float), np.asarray(y, dtype=float), bounds=bounds)
    return {
        "x_labels": list(x_labels),
        "y_actual": [float(v) for v in y],
        "y_pred": fit.y_pred_all.tolist(),
        "ci_lower": fit.ci_lower.tolist(),
        "ci_upper": fit.ci_upper.tolist(),
        "split_index": fit.split_index,
        "holdout_r2": fit.holdout_r2,
        "holdout_rmse": fit.holdout_rmse,
        "metric_label": metric_label,
        "x_title": x_title,
        "hover_extra": list(hover_extra) if hover_extra is not None else None,
        "hover_extra_label": hover_extra_label,
    }


def _empty_payload(metric_label: str, x_title: str) -> dict:
    return {
        "x_labels": [], "y_actual": [], "y_pred": [], "ci_lower": [], "ci_upper": [],
        "split_index": 0, "holdout_r2": None, "holdout_rmse": None,
        "metric_label": metric_label, "x_title": x_title,
        "hover_extra": None, "hover_extra_label": "",
    }


@cached(ttl_seconds=TRAJECTORY_TTL_SECONDS)
def compute_hitter_trajectory(player_id: int, season: int, metric: str) -> dict:
    label = dict(metrics_for_group("hitting")).get(metric, metric)
    game_log = game_log_dataframe(players.get_game_log(player_id, season, "hitting"))
    if game_log.empty or metric not in game_log.columns:
        return _empty_payload(f"{label} (rolling {HITTER_ROLLING_WINDOW}-game)", "Game Date")

    batted_balls = batted_balls_dataframe(statcast.get_batter_batted_balls(player_id, season))
    frame = build_hitter_feature_frame(game_log, batted_balls, metric=metric)
    valid = frame.dropna(subset=["rolling_metric"]).reset_index(drop=True)
    if valid.empty:
        return _empty_payload(f"{label} (rolling {HITTER_ROLLING_WINDOW}-game)", "Game Date")

    bounds = RATE_STAT_BOUNDS if metric in ("avg", "obp", "slg", "ops") else None
    return _payload(
        x_labels=valid["date"].dt.strftime("%Y-%m-%d").tolist(),
        y=valid["rolling_metric"].tolist(),
        X=valid[HITTER_FEATURE_COLUMNS].to_numpy(),
        metric_label=f"{label} (rolling {HITTER_ROLLING_WINDOW}-game)",
        x_title="Game Date",
        hover_extra=valid["opponent"].tolist(),
        hover_extra_label="Opponent",
        bounds=bounds,
    )


@cached(ttl_seconds=TRAJECTORY_TTL_SECONDS)
def compute_pitcher_trajectory(player_id: int, season: int, fallback_metric: str = "era") -> dict:
    """CSW% pitch-level trajectory when Statcast is available; otherwise an
    appearance-level fallback on ``fallback_metric`` from MLB Stats API.
    Always includes ``used_statcast`` so the caller can label the chart.
    """
    pitches = pitches_dataframe(statcast.get_pitcher_pitches(player_id, season))
    if not pitches.empty:
        frame = build_pitcher_csw_frame(pitches)
        payload = _payload(
            x_labels=frame["pitch_index"].tolist(),
            y=frame["rolling_csw"].tolist(),
            X=frame[PITCHER_FEATURE_COLUMNS].to_numpy(),
            metric_label=f"CSW% (rolling {CSW_ROLLING_WINDOW}-pitch)",
            x_title="Pitch Index (season-chronological)",
            bounds=(0.0, 1.0),
        )
        payload["used_statcast"] = True
        return payload

    label = dict(metrics_for_group("pitching")).get(fallback_metric, fallback_metric)
    game_log = game_log_dataframe(players.get_game_log(player_id, season, "pitching"))
    if game_log.empty or fallback_metric not in game_log.columns:
        payload = _empty_payload(label, "Game Date")
        payload["used_statcast"] = False
        return payload

    valid = game_log.dropna(subset=[fallback_metric]).reset_index(drop=True)
    X = np.arange(len(valid)).reshape(-1, 1)
    payload = _payload(
        x_labels=valid["date"].dt.strftime("%Y-%m-%d").tolist(),
        y=valid[fallback_metric].astype(float).tolist(),
        X=X,
        metric_label=label,
        x_title="Game Date",
        hover_extra=valid["opponent"].tolist(),
        hover_extra_label="Opponent",
    )
    payload["used_statcast"] = False
    return payload


@cached(ttl_seconds=TRAJECTORY_TTL_SECONDS)
def compute_team_trajectory(team_id: int, season: int, mode: str) -> dict:
    schedule = schedule_dataframe(teams.get_schedule(team_id, season), team_id)
    label = "Rolling Runs Scored (10-game)" if mode == "offense" else "Rolling Runs Allowed (10-game)"
    if schedule.empty:
        return _empty_payload(label, "Game Date")

    frame = build_team_rolling_frame(schedule)
    y_col = "rolling_runs_for" if mode == "offense" else "rolling_runs_against"
    return _payload(
        x_labels=frame["date"].dt.strftime("%Y-%m-%d").tolist(),
        y=frame[y_col].tolist(),
        X=frame[["game_num"]].to_numpy(),
        metric_label=label,
        x_title="Game Date",
        hover_extra=frame["opponent"].tolist(),
        hover_extra_label="Opponent",
    )


def _empty_forecast_payload(metric_label: str) -> dict:
    return {"years": [], "forecast": [], "ci_lower": [], "ci_upper": [], "actual": [], "metric_label": metric_label}


def compute_forecast_from_series(
    get_series, metric: str, group: str, train_start: int, train_end: int, forecast_end: int
) -> dict:
    """Shared fitting logic behind compute_metric_forecast (player subject),
    compute_team_metric_forecast (team-aggregate subject), and client.py's
    multi-player aggregate forecast -- all three differ only in which
    get_series callable they pull annual actuals from (a single player's
    own season series, a team's aggregate series, or a combined series
    across an arbitrary set of selected players). Public (not the
    trajectories.py-internal helper it started as) precisely because a
    third caller now needs it from outside this module.

    Fits on annual actuals in [train_start, train_end] (every training year
    is used -- no holdout split, unlike the trajectory functions above),
    then forecasts forward through forecast_end.

    The returned "years"/"forecast"/"ci_lower"/"ci_upper" span only
    [train_end, forecast_end] -- the dashboard's Forecast graph draws the
    forecast line starting where the training window ends, not re-drawing
    the training years already shown on the Performance Trend graph.
    "actual" carries real season values wherever they exist in that same
    window (None elsewhere), for a forecast-vs-actual comparison -- never
    for the training years themselves, since those were already used to fit
    the line.
    """
    label = dict(metrics_for_group(group)).get(metric, metric)
    full_series = get_series(metric, group, train_start, forecast_end)
    actual_by_year = dict(zip(full_series["years"], full_series["values"]))

    train_years = [year for year in full_series["years"] if year <= train_end]
    if not train_years:
        return _empty_forecast_payload(label)

    X_train = np.array(train_years, dtype=float).reshape(-1, 1)
    y_train = np.array([actual_by_year[year] for year in train_years], dtype=float)

    forecast_years = list(range(train_end, forecast_end + 1))
    X_full = np.array(forecast_years, dtype=float).reshape(-1, 1)

    bounds = RATE_STAT_BOUNDS if metric in ("avg", "obp", "slg", "ops") else None
    fit = fit_and_forecast(X_train, y_train, X_full, bounds=bounds)

    return {
        "years": forecast_years,
        "forecast": fit.y_pred_all.tolist(),
        "ci_lower": fit.ci_lower.tolist(),
        "ci_upper": fit.ci_upper.tolist(),
        "actual": [actual_by_year.get(year) for year in forecast_years],
        "metric_label": label,
    }


@cached(ttl_seconds=TRAJECTORY_TTL_SECONDS)
def compute_metric_forecast(
    player_id: int, metric: str, group: str, train_start: int, train_end: int, forecast_end: int
) -> dict:
    get_series = lambda m, g, s, e: players.get_season_series(player_id, m, g, s, e)  # noqa: E731
    return compute_forecast_from_series(get_series, metric, group, train_start, train_end, forecast_end)


@cached(ttl_seconds=TRAJECTORY_TTL_SECONDS)
def compute_team_metric_forecast(
    team_id: int, metric: str, group: str, train_start: int, train_end: int, forecast_end: int
) -> dict:
    get_series = lambda m, g, s, e: teams.get_team_season_series(team_id, m, g, s, e)  # noqa: E731
    return compute_forecast_from_series(get_series, metric, group, train_start, train_end, forecast_end)
