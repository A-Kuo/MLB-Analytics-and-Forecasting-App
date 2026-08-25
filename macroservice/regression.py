"""Regression overlays for player/team performance trajectories.

v2 replaces the single-model Ridge fit with a blended probabilistic ensemble
-- SVR(rbf) 35% + HuberRegressor 35% + GaussianProcessRegressor(RBF +
WhiteKernel) 30% -- evaluated on a chronological 80/20 holdout so the
reported R²/RMSE reflect genuine out-of-sample fit. The GPR term also
supplies a 95% confidence band around the blended trajectory.

``fit_regression`` (plain Ridge) is kept for the simple single-feature
trendline case and is still covered by tests/test_regression.py.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel
from sklearn.linear_model import HuberRegressor, Ridge
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR

ENSEMBLE_WEIGHTS = {"svr": 0.35, "huber": 0.35, "gpr": 0.30}
CI_Z_SCORE = 1.96  # ~95% confidence band from the GPR predictive std
MIN_SAMPLES_FOR_ENSEMBLE = 4


def fit_regression(x: list[int], y: list[float], alpha: float = 1.0) -> list[float]:
    """Single-feature Ridge trendline (legacy v1 behavior)."""
    if len(x) < 2:
        return list(y)
    X = np.array(x, dtype=float).reshape(-1, 1)
    model = Ridge(alpha=alpha)
    model.fit(X, np.array(y, dtype=float))
    return model.predict(X).tolist()


@dataclass
class TrajectoryFit:
    y_pred_all: np.ndarray       # blended trajectory over every input row
    ci_lower: np.ndarray         # 95% CI lower band
    ci_upper: np.ndarray         # 95% CI upper band
    split_index: int             # row index where the holdout set begins
    holdout_r2: float | None
    holdout_rmse: float | None


def fit_trajectory_ensemble(
    X: np.ndarray,
    y: np.ndarray,
    train_fraction: float = 0.8,
    bounds: tuple[float, float] | None = None,
) -> TrajectoryFit:
    """Fit the SVR/Huber/GaussianProcess ensemble on a chronological split.

    ``X`` is (n_samples, n_features) ordered chronologically (row 0 =
    earliest); the last ``1 - train_fraction`` rows are held out as an
    out-of-sample test set. Returns a blended trajectory + 95% CI band over
    every row, plus holdout R²/RMSE (``None`` when the holdout has < 2 rows).
    """
    X = np.atleast_2d(np.asarray(X, dtype=float))
    y = np.asarray(y, dtype=float)
    n = len(y)

    if n < MIN_SAMPLES_FOR_ENSEMBLE:
        # Too few points for a meaningful ensemble/holdout split.
        flat = np.full(n, y.mean() if n else 0.0)
        return TrajectoryFit(flat, flat, flat, split_index=n, holdout_r2=None, holdout_rmse=None)

    split = max(2, int(round(n * train_fraction)))
    split = min(split, n - 1)

    X_train, y_train = X[:split], y[:split]
    X_test, y_test = X[split:], y[split:]

    x_scaler = StandardScaler().fit(X_train)
    X_train_s = x_scaler.transform(X_train)
    X_all_s = x_scaler.transform(X)

    y_mean, y_std = y_train.mean(), (y_train.std() or 1.0)
    y_train_s = (y_train - y_mean) / y_std

    svr = SVR(kernel="rbf", C=1.0).fit(X_train_s, y_train_s)
    huber = HuberRegressor().fit(X_train_s, y_train_s)
    kernel = RBF(length_scale=1.0) + WhiteKernel(noise_level=1.0)
    gpr = GaussianProcessRegressor(kernel=kernel, normalize_y=False, n_restarts_optimizer=2)
    with warnings.catch_warnings():
        # The optimizer routinely lands near the noise_level lower bound on
        # small, near-flat rolling-window targets; harmless, just noisy.
        warnings.filterwarnings("ignore", category=ConvergenceWarning)
        gpr.fit(X_train_s, y_train_s)

    svr_pred = svr.predict(X_all_s) * y_std + y_mean
    huber_pred = huber.predict(X_all_s) * y_std + y_mean
    gpr_pred_s, gpr_std_s = gpr.predict(X_all_s, return_std=True)
    gpr_pred = gpr_pred_s * y_std + y_mean
    gpr_std = gpr_std_s * y_std

    blended = (
        ENSEMBLE_WEIGHTS["svr"] * svr_pred
        + ENSEMBLE_WEIGHTS["huber"] * huber_pred
        + ENSEMBLE_WEIGHTS["gpr"] * gpr_pred
    )
    ci_lower = blended - CI_Z_SCORE * gpr_std
    ci_upper = blended + CI_Z_SCORE * gpr_std

    if bounds is not None:
        lo, hi = bounds
        blended = np.clip(blended, lo, hi)
        ci_lower = np.clip(ci_lower, lo, hi)
        ci_upper = np.clip(ci_upper, lo, hi)

    holdout_r2 = holdout_rmse = None
    if len(y_test) >= 2:
        holdout_pred = blended[split:]
        holdout_r2 = float(r2_score(y_test, holdout_pred))
        holdout_rmse = float(np.sqrt(mean_squared_error(y_test, holdout_pred)))

    return TrajectoryFit(
        y_pred_all=blended,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        split_index=split,
        holdout_r2=holdout_r2,
        holdout_rmse=holdout_rmse,
    )


@dataclass
class ForecastFit:
    y_pred_all: np.ndarray   # blended prediction over every row of X_full
    ci_lower: np.ndarray
    ci_upper: np.ndarray


def fit_and_forecast(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_full: np.ndarray,
    bounds: tuple[float, float] | None = None,
) -> ForecastFit:
    """Fit the SVR/Huber/GaussianProcess ensemble on ALL of X_train/y_train
    (no internal holdout split -- unlike fit_trajectory_ensemble, every
    training row is used for fitting), then predict across X_full, which
    includes the training rows plus any additional rows beyond them (e.g.
    future years with no ground truth yet). Regressors extrapolate to new X
    natively via .predict(); this is a fit/predict split, not a
    train/holdout split.
    """
    X_train = np.atleast_2d(np.asarray(X_train, dtype=float))
    y_train = np.asarray(y_train, dtype=float)
    X_full = np.atleast_2d(np.asarray(X_full, dtype=float))
    n_train = len(y_train)

    if n_train < MIN_SAMPLES_FOR_ENSEMBLE:
        # Too few training points for a meaningful ensemble fit.
        flat = np.full(len(X_full), y_train.mean() if n_train else 0.0)
        return ForecastFit(flat, flat, flat)

    x_scaler = StandardScaler().fit(X_train)
    X_train_s = x_scaler.transform(X_train)
    X_full_s = x_scaler.transform(X_full)

    y_mean, y_std = y_train.mean(), (y_train.std() or 1.0)
    y_train_s = (y_train - y_mean) / y_std

    svr = SVR(kernel="rbf", C=1.0).fit(X_train_s, y_train_s)
    huber = HuberRegressor().fit(X_train_s, y_train_s)
    kernel = RBF(length_scale=1.0) + WhiteKernel(noise_level=1.0)
    gpr = GaussianProcessRegressor(kernel=kernel, normalize_y=False, n_restarts_optimizer=2)
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=ConvergenceWarning)
        gpr.fit(X_train_s, y_train_s)

    svr_pred = svr.predict(X_full_s) * y_std + y_mean
    huber_pred = huber.predict(X_full_s) * y_std + y_mean
    gpr_pred_s, gpr_std_s = gpr.predict(X_full_s, return_std=True)
    gpr_pred = gpr_pred_s * y_std + y_mean
    gpr_std = gpr_std_s * y_std

    blended = (
        ENSEMBLE_WEIGHTS["svr"] * svr_pred
        + ENSEMBLE_WEIGHTS["huber"] * huber_pred
        + ENSEMBLE_WEIGHTS["gpr"] * gpr_pred
    )
    ci_lower = blended - CI_Z_SCORE * gpr_std
    ci_upper = blended + CI_Z_SCORE * gpr_std

    if bounds is not None:
        lo, hi = bounds
        blended = np.clip(blended, lo, hi)
        ci_lower = np.clip(ci_lower, lo, hi)
        ci_upper = np.clip(ci_upper, lo, hi)

    return ForecastFit(y_pred_all=blended, ci_lower=ci_lower, ci_upper=ci_upper)
