"""Loads one PyTorch team-forecast results JSON (see the plan's "Results
JSON schema") into the Postgres team_forecast_* tables.

This is a one-shot loader, not a backfill loop: there's exactly one JSON
artifact per notebook run (produced by a smoke-test notebook locally, or
downloaded after a real GPU run on Kaggle), so the whole load is one
transaction -- a partial load (run metadata written but holdout rows
failed) is a worse state than "load failed, try again", unlike
scripts/backfill_roster_history.py's 30 independently-recoverable
per-team API calls.

Usage:
    python scripts/load_team_forecasts.py notebooks/results/season_aggregate-2026.08.26-0100-smoke.json
    python scripts/load_team_forecasts.py path/to/results.json --no-set-active

Reads the connection string the same way backfill_roster_history.py does
(DATABASE_URL env var / .env / local .streamlit/secrets.toml) -- this runs
outside Streamlit entirely.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).parent.parent))

from macroservice import db  # noqa: E402  (needs the path insert above)

REQUIRED_KEYS = (
    "track",
    "model_version",
    "run_timestamp_utc",
    "environment",
    "training_window",
    "holdout_window",
    "targets",
    "aggregate_holdout_metrics",
    "holdout_predictions",
    "forward_forecasts",
)

_UPSERT_RUN_SQL = text('''
    INSERT INTO team_forecast_runs
        (model_version, track, run_timestamp, environment, training_start_year, training_end_year,
         holdout_start_year, holdout_end_year, hyperparameters, notes)
    VALUES
        (:model_version, :track, :run_timestamp, :environment, :training_start_year, :training_end_year,
         :holdout_start_year, :holdout_end_year, :hyperparameters, :notes)
    ON CONFLICT (model_version) DO UPDATE SET
        track = EXCLUDED.track, run_timestamp = EXCLUDED.run_timestamp, environment = EXCLUDED.environment,
        training_start_year = EXCLUDED.training_start_year, training_end_year = EXCLUDED.training_end_year,
        holdout_start_year = EXCLUDED.holdout_start_year, holdout_end_year = EXCLUDED.holdout_end_year,
        hyperparameters = EXCLUDED.hyperparameters, notes = EXCLUDED.notes
''')

_UPSERT_HOLDOUT_SQL = text('''
    INSERT INTO team_forecast_holdout (model_version, team_id, year, metric, actual, predicted)
    VALUES (:model_version, :team_id, :year, :metric, :actual, :predicted)
    ON CONFLICT (model_version, team_id, year, metric) DO UPDATE SET
        actual = EXCLUDED.actual, predicted = EXCLUDED.predicted
''')

_UPSERT_PREDICTIONS_SQL = text('''
    INSERT INTO team_forecast_predictions (model_version, team_id, year, metric, predicted, ci_lower, ci_upper)
    VALUES (:model_version, :team_id, :year, :metric, :predicted, :ci_lower, :ci_upper)
    ON CONFLICT (model_version, team_id, year, metric) DO UPDATE SET
        predicted = EXCLUDED.predicted, ci_lower = EXCLUDED.ci_lower, ci_upper = EXCLUDED.ci_upper
''')

_UPSERT_METRICS_SQL = text('''
    INSERT INTO team_forecast_metrics (model_version, metric, holdout_r2, holdout_rmse, n_holdout)
    VALUES (:model_version, :metric, :holdout_r2, :holdout_rmse, :n_holdout)
    ON CONFLICT (model_version, metric) DO UPDATE SET
        holdout_r2 = EXCLUDED.holdout_r2, holdout_rmse = EXCLUDED.holdout_rmse, n_holdout = EXCLUDED.n_holdout
''')

_DEACTIVATE_OTHERS_SQL = text(
    "UPDATE team_forecast_runs SET is_active = FALSE WHERE track = :track AND model_version != :model_version"
)
_ACTIVATE_THIS_SQL = text("UPDATE team_forecast_runs SET is_active = TRUE WHERE model_version = :model_version")


def validate_results(results: dict) -> None:
    missing = [key for key in REQUIRED_KEYS if key not in results]
    if missing:
        raise ValueError(f"Results JSON is missing required key(s): {', '.join(missing)}")


def load_results(engine, results: dict, set_active: bool = True) -> None:
    validate_results(results)
    model_version = results["model_version"]

    with engine.begin() as conn:
        conn.execute(
            _UPSERT_RUN_SQL,
            {
                "model_version": model_version,
                "track": results["track"],
                "run_timestamp": results["run_timestamp_utc"],
                "environment": results["environment"],
                "training_start_year": results["training_window"]["start_year"],
                "training_end_year": results["training_window"]["end_year"],
                "holdout_start_year": results["holdout_window"]["start_year"],
                "holdout_end_year": results["holdout_window"]["end_year"],
                "hyperparameters": json.dumps(results.get("hyperparameters") or {}),
                "notes": results.get("notes"),
            },
        )

        if results["holdout_predictions"]:
            conn.execute(
                _UPSERT_HOLDOUT_SQL,
                [
                    {
                        "model_version": model_version,
                        "team_id": row["team_id"],
                        "year": row["year"],
                        "metric": row["metric"],
                        "actual": row.get("actual"),
                        "predicted": row["predicted"],
                    }
                    for row in results["holdout_predictions"]
                ],
            )

        if results["forward_forecasts"]:
            conn.execute(
                _UPSERT_PREDICTIONS_SQL,
                [
                    {
                        "model_version": model_version,
                        "team_id": row["team_id"],
                        "year": row["year"],
                        "metric": row["metric"],
                        "predicted": row["predicted"],
                        "ci_lower": row.get("ci_lower"),
                        "ci_upper": row.get("ci_upper"),
                    }
                    for row in results["forward_forecasts"]
                ],
            )

        metrics_rows = [
            {
                "model_version": model_version,
                "metric": metric,
                "holdout_r2": stats.get("r2"),
                "holdout_rmse": stats.get("rmse"),
                "n_holdout": stats.get("n"),
            }
            for metric, stats in results["aggregate_holdout_metrics"].items()
        ]
        if metrics_rows:
            conn.execute(_UPSERT_METRICS_SQL, metrics_rows)

        if set_active:
            conn.execute(_DEACTIVATE_OTHERS_SQL, {"track": results["track"], "model_version": model_version})
            conn.execute(_ACTIVATE_THIS_SQL, {"model_version": model_version})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results_path", type=Path, help="Path to a results JSON file")
    parser.add_argument(
        "--no-set-active",
        action="store_true",
        help="Load the run's rows without marking it the active run for its track",
    )
    args = parser.parse_args()

    if not args.results_path.is_file():
        print(f"No such file: {args.results_path}", file=sys.stderr)
        return 2

    try:
        results = json.loads(args.results_path.read_text())
    except json.JSONDecodeError as exc:
        print(f"Malformed JSON in {args.results_path}: {exc}", file=sys.stderr)
        return 2

    try:
        validate_results(results)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    load_dotenv()
    database_url = db.resolve_database_url()
    if not database_url:
        print(
            "No database connection string found -- set DATABASE_URL (environment or .env), "
            "or configure [connections.postgresql].url in .streamlit/secrets.toml.",
            file=sys.stderr,
        )
        return 2

    engine = create_engine(database_url)
    db.ensure_schema(engine)
    load_results(engine, results, set_active=not args.no_set_active)

    n_holdout = len(results["holdout_predictions"])
    n_forecast = len(results["forward_forecasts"])
    print(f"Loaded {results['model_version']} ({results['track']}): {n_holdout} holdout rows, {n_forecast} forecast rows.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
