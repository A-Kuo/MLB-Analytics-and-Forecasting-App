"""Walk-forward evaluation of the season-level forecast models.

Evaluates the same task the Analytics page performs -- predicting a player's
future season value of one metric from year alone -- using an expanding-window
walk-forward split: at each origin the models are fit only on seasons before
it, then scored on the next ``h`` seasons (h in --horizons). Nothing from the
scored season is ever visible to a fit.

Models: two naive baselines (last observed value, expanding mean), the
six-model zoo (Ridge, Huber, SVR, Gaussian Process, Random Forest,
HistGradientBoosting), and the production ensemble
(macroservice.regression.fit_and_forecast -- the fixed 0.35/0.35/0.30
SVR/Huber/GPR blend the app actually serves, also used to score the 90%
interval's empirical coverage).

Reads season stats from Postgres (DATABASE_URL, same as the other scripts):

    python scripts/evaluate_forecasts.py
    python scripts/evaluate_forecasts.py --metric home_runs --players 150

Writes notebooks/results/forecast_eval-<metric>-<date>.json and prints a
markdown table. The stats tables carry no plate-appearance counts, so
part-time seasons cannot be filtered out; --min-seasons (default 10) is only
a coarse proxy for regulars.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import warnings
from datetime import date
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from joblib import Parallel, delayed
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.exceptions import ConvergenceWarning
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel
from sklearn.linear_model import HuberRegressor, Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).parent.parent))

from macroservice import db  # noqa: E402  (needs the path insert above)
from macroservice.regression import fit_and_forecast  # noqa: E402

# column allowlist -- interpolated into SQL below, never taken from raw input
HITTING_COLUMNS = {"avg", "obp", "slg", "ops", "home_runs", "rbi", "strikeouts", "walks"}
RATE_COLUMNS = {"avg", "obp", "slg", "ops"}
RATE_BOUNDS = (0.0, 1.5)  # matches trajectories.RATE_STAT_BOUNDS
MIN_TRAIN = 6
MODELS = ["naive_last", "naive_mean", "ridge", "huber", "svr", "gpr", "random_forest", "hist_gbm", "ensemble"]


def _fit_predict_zoo(x_train: np.ndarray, y_train: np.ndarray, x_new: np.ndarray, seed: int) -> dict[str, np.ndarray]:
    scaler = StandardScaler().fit(x_train)
    xt, xn = scaler.transform(x_train), scaler.transform(x_new)
    y_mean, y_std = y_train.mean(), (y_train.std() or 1.0)
    ys = (y_train - y_mean) / y_std

    def back(p):
        return np.asarray(p) * y_std + y_mean

    out = {
        "ridge": back(Ridge(alpha=1.0).fit(xt, ys).predict(xn)),
        "huber": back(HuberRegressor().fit(xt, ys).predict(xn)),
        "svr": back(SVR(kernel="rbf", C=1.0).fit(xt, ys).predict(xn)),
        "random_forest": back(RandomForestRegressor(n_estimators=100, random_state=seed).fit(xt, ys).predict(xn)),
        "hist_gbm": back(
            HistGradientBoostingRegressor(min_samples_leaf=2, max_iter=100, random_state=seed).fit(xt, ys).predict(xn)
        ),
    }
    kernel = RBF(length_scale=1.0) + WhiteKernel(noise_level=0.3, noise_level_bounds=(1e-5, 0.5))
    gpr = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=8, random_state=seed).fit(xt, ys)
    out["gpr"] = back(gpr.predict(xn))
    return out


def _evaluate_player(years: list[int], values: list[float], horizons: list[int], bounds, seed: int) -> list[dict]:
    """One row per (origin, horizon) with every model's prediction."""
    y = np.asarray(values, dtype=float)
    x = np.asarray(years, dtype=float).reshape(-1, 1)
    max_h = max(horizons)
    rows = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=ConvergenceWarning)
        warnings.simplefilter("ignore", category=RuntimeWarning)
        for origin in range(MIN_TRAIN, len(y)):
            n_ahead = min(max_h, len(y) - origin)
            x_new = x[origin : origin + n_ahead]
            x_train, y_train = x[:origin], y[:origin]
            preds = _fit_predict_zoo(x_train, y_train, x_new, seed)
            if bounds is not None:
                preds = {k: np.clip(v, *bounds) for k, v in preds.items()}
            ens = fit_and_forecast(x_train, y_train, x_new, bounds=bounds)
            preds["ensemble"] = ens.y_pred_all
            preds["naive_last"] = np.full(n_ahead, y_train[-1])
            preds["naive_mean"] = np.full(n_ahead, y_train.mean())
            for h in horizons:
                if h > n_ahead:
                    continue
                rows.append(
                    {
                        "h": h,
                        "actual": float(y[origin + h - 1]),
                        "pred": {m: float(preds[m][h - 1]) for m in MODELS},
                        "ci": [float(ens.ci_lower[h - 1]), float(ens.ci_upper[h - 1])],
                    }
                )
    return rows


def _summarize(per_player: list[list[dict]], horizons: list[int], seed: int, n_boot: int = 1000) -> dict:
    rng = np.random.default_rng(seed)
    result: dict = {}
    for h in horizons:
        by_player = [[r for r in rows if r["h"] == h] for rows in per_player]
        by_player = [rows for rows in by_player if rows]
        actual = np.array([r["actual"] for rows in by_player for r in rows])
        owner = np.array([i for i, rows in enumerate(by_player) for _ in rows])
        preds = {m: np.array([r["pred"][m] for rows in by_player for r in rows]) for m in MODELS}
        mse_naive = float(np.mean((actual - preds["naive_last"]) ** 2))
        ss_tot = float(np.sum((actual - actual.mean()) ** 2))
        table = {}
        for m in MODELS:
            err = actual - preds[m]
            table[m] = {
                "mae": float(np.mean(np.abs(err))),
                "rmse": float(np.sqrt(np.mean(err**2))),
                "r2_pooled": float(1 - np.sum(err**2) / ss_tot),
                "mse_skill_vs_naive_last": float(1 - np.mean(err**2) / mse_naive),
            }
        # player-clustered bootstrap: ensemble MAE minus naive-last MAE
        n_players = len(by_player)
        diff = np.abs(actual - preds["ensemble"]) - np.abs(actual - preds["naive_last"])
        per_player_diff = np.array([diff[owner == i].mean() for i in range(n_players)])
        boots = [per_player_diff[rng.integers(0, n_players, n_players)].mean() for _ in range(n_boot)]
        lo = np.array([r["ci"][0] for rows in by_player for r in rows])
        hi = np.array([r["ci"][1] for rows in by_player for r in rows])
        result[str(h)] = {
            "n_predictions": int(len(actual)),
            "n_players": n_players,
            "models": table,
            "ensemble_minus_naive_last_mae": {
                "mean": float(per_player_diff.mean()),
                "ci95": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))],
            },
            "ensemble_90pct_interval_coverage": float(np.mean((actual >= lo) & (actual <= hi))),
        }
    return result


def _load_series(engine, column: str, min_seasons: int) -> dict[int, tuple[list[int], list[float]]]:
    sql = text(
        f"SELECT player_id, season, {column} AS value FROM player_season_hitting_stats "
        f"WHERE {column} IS NOT NULL ORDER BY player_id, season"
    )
    series: dict[int, tuple[list[int], list[float]]] = {}
    with engine.connect() as conn:
        for row in conn.execute(sql).mappings():
            years, vals = series.setdefault(int(row["player_id"]), ([], []))
            years.append(int(row["season"]))
            vals.append(float(row["value"]))
    return {pid: s for pid, s in series.items() if len(s[0]) >= min_seasons}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--metric", default="ops", choices=sorted(HITTING_COLUMNS))
    parser.add_argument("--players", type=int, default=100, help="random sample size (fixed --seed)")
    parser.add_argument("--min-seasons", type=int, default=10)
    parser.add_argument("--horizons", default="1,3")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--jobs", type=int, default=-1)
    args = parser.parse_args()
    horizons = sorted({int(h) for h in args.horizons.split(",")})

    load_dotenv()
    url = db.resolve_database_url()
    if not url:
        print("No database connection string found -- set DATABASE_URL (environment or .env).", file=sys.stderr)
        return 1
    engine = create_engine(url)

    series = _load_series(engine, args.metric, args.min_seasons)
    ids = sorted(series)
    sampled = random.Random(args.seed).sample(ids, min(args.players, len(ids)))
    print(f"{len(ids)} eligible players (>= {args.min_seasons} seasons of {args.metric}); evaluating {len(sampled)}")

    bounds = RATE_BOUNDS if args.metric in RATE_COLUMNS else None
    per_player = Parallel(n_jobs=args.jobs, verbose=5)(
        delayed(_evaluate_player)(*series[pid], horizons, bounds, args.seed) for pid in sampled
    )
    summary = _summarize(per_player, horizons, args.seed)

    out = {
        "script": "scripts/evaluate_forecasts.py",
        "run_date": date.today().isoformat(),
        "metric": args.metric,
        "min_seasons": args.min_seasons,
        "min_train_seasons": MIN_TRAIN,
        "seed": args.seed,
        "eligible_players": len(ids),
        "sampled_player_ids": sampled,
        "results_by_horizon": summary,
    }
    out_path = Path(__file__).parent.parent / "notebooks" / "results" / f"forecast_eval-{args.metric}-{out['run_date']}.json"
    out_path.write_text(json.dumps(out, indent=2))

    for h, block in summary.items():
        print(f"\nHorizon {h} season(s) ahead -- {block['n_predictions']} predictions over {block['n_players']} players")
        print("| Model | MAE | RMSE | R² (pooled) | MSE skill vs naive-last |")
        print("|---|---|---|---|---|")
        for m, v in block["models"].items():
            print(f"| {m} | {v['mae']:.4f} | {v['rmse']:.4f} | {v['r2_pooled']:.3f} | {v['mse_skill_vs_naive_last']:+.3f} |")
        d = block["ensemble_minus_naive_last_mae"]
        print(f"ensemble MAE - naive_last MAE: {d['mean']:+.4f} (95% bootstrap CI {d['ci95'][0]:+.4f} to {d['ci95'][1]:+.4f})")
        print(f"90% interval empirical coverage: {block['ensemble_90pct_interval_coverage']:.1%}")
    print(f"\nWrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
