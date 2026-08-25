from utils.filters import (
    HITTING_METRICS,
    PITCHING_METRICS,
    full_name_for_metric,
    is_rate_metric,
    metrics_for_group,
    stat_group_for_position,
)


def test_pitchers_get_pitching_group():
    assert stat_group_for_position("P") == "pitching"


def test_non_pitchers_get_hitting_group():
    assert stat_group_for_position("RF") == "hitting"
    assert stat_group_for_position("C") == "hitting"


def test_metrics_for_group_selects_the_right_list():
    assert metrics_for_group("pitching") == PITCHING_METRICS
    assert metrics_for_group("hitting") == HITTING_METRICS


def test_every_metric_has_a_full_name():
    for key, _ in HITTING_METRICS + PITCHING_METRICS:
        assert full_name_for_metric(key) != key, f"{key} is missing a full name"


def test_full_name_falls_back_to_the_key():
    assert full_name_for_metric("noSuchMetric") == "noSuchMetric"


def test_rate_metrics_are_classified_as_rates():
    for key in ("avg", "obp", "slg", "ops", "era", "whip"):
        assert is_rate_metric(key)


def test_counting_metrics_are_not_classified_as_rates():
    for key in ("homeRuns", "rbi", "strikeOuts", "baseOnBalls", "inningsPitched", "earnedRuns"):
        assert not is_rate_metric(key)
