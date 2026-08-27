"""Tests for scripts/load_team_forecasts.py.

Mocks the SQLAlchemy Engine/Connection rather than touching a real
database, matching tests/test_roster_history_db.py's pattern.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import load_team_forecasts  # noqa: E402


def _writable_engine():
    engine = MagicMock()
    conn = engine.begin.return_value.__enter__.return_value
    return engine, conn


def _results(**overrides):
    base = {
        "schema_version": "1.0",
        "track": "season_aggregate",
        "model_version": "season_aggregate-2026.08.26-0100-smoke",
        "run_timestamp_utc": "2026-08-26T18:04:00Z",
        "environment": "local_smoke",
        "git_commit": "abc1234",
        "random_seed": 42,
        "hyperparameters": {"hidden_dims": [8, 8], "epochs_trained": 30},
        "targets": ["win_pct"],
        "feature_list": ["year_norm"],
        "teams": [{"team_id": 147, "abbreviation": "NYY", "embedding_index": 0}],
        "training_window": {"start_year": 1901, "end_year": 2014},
        "holdout_window": {"start_year": 2015, "end_year": 2025},
        "regime_flags_used": [],
        "excluded_rows": [],
        "baseline_comparison": {"win_pct": {"r2": 0.01, "rmse": 0.05}},
        "aggregate_holdout_metrics": {"win_pct": {"r2": 0.12, "rmse": 0.04, "n": 55}},
        "holdout_predictions": [{"team_id": 147, "year": 2015, "metric": "win_pct", "actual": 0.463, "predicted": 0.48}],
        "forward_forecasts": [{"team_id": 147, "year": 2026, "metric": "win_pct", "predicted": 0.51, "ci_lower": None, "ci_upper": None}],
        "loss_curve": {"train": [1.0, 0.9], "val": [1.1, 0.95]},
        "notes": "",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# validate_results
# ---------------------------------------------------------------------------


def test_validate_results_passes_for_a_complete_payload():
    load_team_forecasts.validate_results(_results())  # should not raise


def test_validate_results_raises_on_missing_required_key():
    incomplete = _results()
    del incomplete["model_version"]
    with pytest.raises(ValueError, match="model_version"):
        load_team_forecasts.validate_results(incomplete)


def test_validate_results_lists_every_missing_key():
    incomplete = _results()
    del incomplete["track"]
    del incomplete["targets"]
    with pytest.raises(ValueError, match="track.*targets|targets.*track"):
        load_team_forecasts.validate_results(incomplete)


# ---------------------------------------------------------------------------
# load_results
# ---------------------------------------------------------------------------


def test_load_results_runs_inside_one_transaction():
    engine, conn = _writable_engine()
    load_team_forecasts.load_results(engine, _results())
    engine.begin.assert_called_once()
    assert conn.execute.called


def test_load_results_upserts_the_run_row_with_correct_params():
    engine, conn = _writable_engine()
    load_team_forecasts.load_results(engine, _results())
    run_call = conn.execute.call_args_list[0]
    params = run_call[0][1]
    assert params["model_version"] == "season_aggregate-2026.08.26-0100-smoke"
    assert params["track"] == "season_aggregate"
    assert params["training_start_year"] == 1901
    assert params["holdout_end_year"] == 2025


def test_load_results_upserts_holdout_predictions_forecasts_and_metrics():
    engine, conn = _writable_engine()
    load_team_forecasts.load_results(engine, _results())
    all_sql_texts = [str(call[0][0]) for call in conn.execute.call_args_list]
    assert any("team_forecast_holdout" in s for s in all_sql_texts)
    assert any("team_forecast_predictions" in s for s in all_sql_texts)
    assert any("team_forecast_metrics" in s for s in all_sql_texts)


def test_load_results_skips_holdout_upsert_when_no_holdout_rows():
    engine, conn = _writable_engine()
    load_team_forecasts.load_results(engine, _results(holdout_predictions=[]))
    all_sql_texts = [str(call[0][0]) for call in conn.execute.call_args_list]
    assert not any("team_forecast_holdout" in s for s in all_sql_texts)


def test_load_results_activates_this_run_and_deactivates_others_by_default():
    engine, conn = _writable_engine()
    load_team_forecasts.load_results(engine, _results())
    all_sql_texts = [str(call[0][0]) for call in conn.execute.call_args_list]
    assert any("is_active = FALSE" in s for s in all_sql_texts)
    assert any("is_active = TRUE" in s for s in all_sql_texts)


def test_load_results_set_active_false_skips_activation_statements():
    engine, conn = _writable_engine()
    load_team_forecasts.load_results(engine, _results(), set_active=False)
    all_sql_texts = [str(call[0][0]) for call in conn.execute.call_args_list]
    assert not any("is_active" in s for s in all_sql_texts)


def test_load_results_raises_before_touching_the_database_on_malformed_input():
    engine, conn = _writable_engine()
    incomplete = _results()
    del incomplete["aggregate_holdout_metrics"]
    with pytest.raises(ValueError):
        load_team_forecasts.load_results(engine, incomplete)
    engine.begin.assert_not_called()
