from chart import build_trajectory_figure


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
