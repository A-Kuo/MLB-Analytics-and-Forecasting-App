import numpy as np

from regression import fit_regression, fit_trajectory_ensemble


def test_single_point_returned_unchanged():
    assert fit_regression([0], [0.300]) == [0.300]


def test_output_length_matches_input():
    x = [0, 1, 2, 3, 4]
    y = [0.250, 0.280, 0.260, 0.310, 0.300]
    assert len(fit_regression(x, y)) == len(x)


def test_flat_input_yields_flat_trend():
    x = [0, 1, 2, 3]
    y = [0.300, 0.300, 0.300, 0.300]
    predictions = fit_regression(x, y)
    assert all(abs(p - 0.300) < 1e-6 for p in predictions)


def test_ensemble_too_few_samples_falls_back_to_flat_mean():
    X = np.array([[0], [1], [2]])
    y = np.array([0.1, 0.3, 0.2])
    fit = fit_trajectory_ensemble(X, y)
    assert fit.holdout_r2 is None
    assert fit.holdout_rmse is None
    assert np.allclose(fit.y_pred_all, y.mean())


def test_ensemble_output_shape_and_holdout_metrics():
    n = 30
    X = np.arange(n).reshape(-1, 1).astype(float)
    y = 0.250 + 0.002 * X[:, 0] + np.random.default_rng(0).normal(0, 0.01, n)
    fit = fit_trajectory_ensemble(X, y)
    assert len(fit.y_pred_all) == n
    assert len(fit.ci_lower) == n
    assert len(fit.ci_upper) == n
    assert fit.split_index == round(n * 0.8)
    assert fit.holdout_r2 is not None
    assert fit.holdout_rmse is not None
    assert np.all(fit.ci_lower <= fit.ci_upper)


def test_ensemble_respects_bounds():
    n = 20
    X = np.arange(n).reshape(-1, 1).astype(float)
    y = np.linspace(0.9, 1.3, n)  # would otherwise extrapolate above 1.0
    fit = fit_trajectory_ensemble(X, y, bounds=(0.0, 1.0))
    assert np.all(fit.y_pred_all <= 1.0)
    assert np.all(fit.y_pred_all >= 0.0)
    assert np.all(fit.ci_upper <= 1.0)
    assert np.all(fit.ci_lower >= 0.0)


def test_ensemble_handles_multifeature_input():
    n = 15
    rng = np.random.default_rng(1)
    X = rng.normal(size=(n, 5))
    y = rng.normal(0.3, 0.05, n)
    fit = fit_trajectory_ensemble(X, y)
    assert len(fit.y_pred_all) == n
