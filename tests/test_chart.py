from chart import build_forecast_figure, build_multi_metric_figure, build_trajectory_figure


def _series(start=2018, n=5, base=0.700, step=0.01):
    return {
        "years": [start + i for i in range(n)],
        "values": [base + step * i for i in range(n)],
    }


def _forecast_payload(start=2020, n=4, base=0.700, step=0.01, actual=None):
    years = [start + i for i in range(n)]
    return {
        "years": years,
        "forecast": [base + step * i for i in range(n)],
        "ci_lower": [base + step * i - 0.02 for i in range(n)],
        "ci_upper": [base + step * i + 0.02 for i in range(n)],
        "actual": actual if actual is not None else [None] * n,
    }


def test_multi_metric_one_trace_per_selected_metric():
    fig = build_multi_metric_figure(
        {"ops": _series(), "avg": _series(base=0.250)}, {"ops": "OPS", "avg": "AVG"}
    )
    assert [t.name for t in fig.data] == ["OPS", "AVG"]


def test_multi_metric_legend_uses_acronyms_not_full_names():
    fig = build_multi_metric_figure({"homeRuns": _series(base=20, step=2)}, {"homeRuns": "HR"})
    assert fig.data[0].name == "HR"


def test_multi_metric_reveal_truncates_every_series():
    fig = build_multi_metric_figure(
        {"ops": _series(n=5), "avg": _series(n=5)}, {"ops": "OPS", "avg": "AVG"}, reveal_upto=2
    )
    for trace in fig.data:
        assert len(trace.x) == 2
        assert len(trace.y) == 2


def test_multi_metric_reveal_none_draws_full_series():
    fig = build_multi_metric_figure({"ops": _series(n=5)}, {"ops": "OPS"}, reveal_upto=None)
    assert len(fig.data[0].x) == 5


def test_multi_metric_splits_rate_and_counting_stats_across_axes():
    fig = build_multi_metric_figure(
        {"avg": _series(base=0.250), "homeRuns": _series(base=30, step=2)},
        {"avg": "AVG", "homeRuns": "HR"},
    )
    axis_by_name = {t.name: t.yaxis for t in fig.data}
    assert axis_by_name["AVG"] == "y"
    assert axis_by_name["HR"] == "y2"
    assert fig.layout.yaxis2.overlaying == "y"


def test_multi_metric_all_rate_stats_share_one_axis():
    fig = build_multi_metric_figure(
        {"avg": _series(base=0.250), "ops": _series()}, {"avg": "AVG", "ops": "OPS"}
    )
    assert {t.yaxis for t in fig.data} == {"y"}
    # No second axis is created at all when nothing needs one.
    assert "yaxis2" not in fig.layout


def test_multi_metric_all_counting_stats_share_one_axis():
    fig = build_multi_metric_figure(
        {"homeRuns": _series(base=30, step=2), "rbi": _series(base=90, step=5)},
        {"homeRuns": "HR", "rbi": "RBI"},
    )
    assert {t.yaxis for t in fig.data} == {"y"}


def test_multi_metric_distinct_color_per_metric():
    fig = build_multi_metric_figure(
        {"avg": _series(), "obp": _series(), "slg": _series()},
        {"avg": "AVG", "obp": "OBP", "slg": "SLG"},
    )
    colors = [t.line.color for t in fig.data]
    assert len(set(colors)) == 3


def _payload(n=10, split=8, hover_extra=None):
    return {
        "x_labels": [f"2026-04-{i + 1:02d}" for i in range(n)],
        "y_actual": [0.250 + 0.005 * i for i in range(n)],
        "y_pred": [0.250 + 0.004 * i for i in range(n)],
        "ci_lower": [0.240 + 0.004 * i for i in range(n)],
        "ci_upper": [0.260 + 0.004 * i for i in range(n)],
        "split_index": split,
        "holdout_r2": 0.42,
        "holdout_rmse": 0.01,
        "metric_label": "AVG",
        "x_title": "Game Date",
        "hover_extra": hover_extra,
        "hover_extra_label": "Opponent" if hover_extra else "",
    }


def test_builds_figure_with_holdout_split():
    fig = build_trajectory_figure(_payload(), series_color="#0C2340")
    trace_names = [trace.name for trace in fig.data]
    assert "Train (actual)" in trace_names
    assert "Holdout (actual)" in trace_names
    assert "95% CI" in trace_names


def test_builds_figure_with_no_holdout_when_split_equals_n():
    fig = build_trajectory_figure(_payload(n=3, split=3), series_color="#0C2340")
    trace_names = [trace.name for trace in fig.data]
    assert "Holdout (actual)" not in trace_names


def test_holdout_metrics_appear_in_title():
    fig = build_trajectory_figure(_payload(), series_color="#0C2340")
    assert "R²=0.420" in fig.layout.title.text


def test_hover_extra_customdata_is_sliced_by_split():
    hover_extra = [f"Opp {i}" for i in range(10)]
    fig = build_trajectory_figure(_payload(hover_extra=hover_extra), series_color="#0C2340")
    train_trace = next(t for t in fig.data if t.name == "Train (actual)")
    holdout_trace = next(t for t in fig.data if t.name == "Holdout (actual)")
    assert list(train_trace.customdata) == hover_extra[:8]
    assert list(holdout_trace.customdata) == hover_extra[8:]


def test_forecast_figure_has_ci_forecast_and_no_actual_trace_when_absent():
    fig = build_forecast_figure({"ops": _forecast_payload()}, {"ops": "OPS"})
    names = [t.name for t in fig.data]
    assert "OPS 95% CI" in names
    assert "OPS forecast" in names
    assert "OPS actual" not in names


def test_forecast_figure_adds_actual_trace_only_for_non_none_years():
    payload = _forecast_payload(n=4, actual=[0.71, None, 0.73, None])
    fig = build_forecast_figure({"ops": payload}, {"ops": "OPS"})
    actual_trace = next(t for t in fig.data if t.name == "OPS actual")
    assert list(actual_trace.x) == [2020, 2022]
    assert list(actual_trace.y) == [0.71, 0.73]


def test_forecast_figure_one_set_of_traces_per_metric():
    fig = build_forecast_figure(
        {"ops": _forecast_payload(base=0.700), "avg": _forecast_payload(base=0.250)},
        {"ops": "OPS", "avg": "AVG"},
    )
    names = {t.name for t in fig.data}
    assert {"OPS 95% CI", "OPS forecast", "AVG 95% CI", "AVG forecast"} <= names


def test_forecast_figure_reveal_truncates_every_series():
    fig = build_forecast_figure(
        {"ops": _forecast_payload(n=4, actual=[0.71, 0.72, 0.73, 0.74])}, {"ops": "OPS"}, reveal_upto=2
    )
    forecast_trace = next(t for t in fig.data if t.name == "OPS forecast")
    actual_trace = next(t for t in fig.data if t.name == "OPS actual")
    assert len(forecast_trace.x) == 2
    assert len(actual_trace.x) == 2


def test_forecast_figure_skips_empty_series_without_erroring():
    fig = build_forecast_figure({"ops": _forecast_payload(n=0)}, {"ops": "OPS"})
    assert fig is not None
    assert not any(t.name == "OPS 95% CI" for t in fig.data)


def test_forecast_figure_splits_rate_and_counting_stats_across_axes():
    fig = build_forecast_figure(
        {"avg": _forecast_payload(base=0.250), "homeRuns": _forecast_payload(base=30, step=2)},
        {"avg": "AVG", "homeRuns": "HR"},
    )
    forecast_axis_by_name = {t.name: t.yaxis for t in fig.data if t.name in ("AVG forecast", "HR forecast")}
    assert forecast_axis_by_name["AVG forecast"] == "y"
    assert forecast_axis_by_name["HR forecast"] == "y2"
