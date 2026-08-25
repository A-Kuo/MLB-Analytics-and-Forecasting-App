from utils.filters import (
    HITTING_METRICS,
    PITCHING_METRICS,
    STATCAST_METRIC_KEYS,
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


def test_statcast_metric_keys_appear_in_the_relevant_metric_lists():
    hitting_keys = {key for key, _ in HITTING_METRICS}
    pitching_keys = {key for key, _ in PITCHING_METRICS}
    assert {"xba", "avgExitVelocity", "hardHitPct", "barrelPct"} <= hitting_keys
    assert {"cswPct", "whiffPct", "chasePct", "avgVelocity"} <= pitching_keys
    # every Statcast key lives in exactly one of the two groups
    assert STATCAST_METRIC_KEYS <= (hitting_keys | pitching_keys)


def test_statcast_percentages_are_rate_metrics():
    for key in ("xba", "hardHitPct", "barrelPct", "cswPct", "whiffPct", "chasePct"):
        assert is_rate_metric(key)


def test_statcast_velocities_are_not_rate_metrics():
    # ~85-105 mph -- closer in scale to counting stats than to a 0-1 rate;
    # must stay off the rate axis or it flattens against a .300 average.
    for key in ("avgExitVelocity", "avgVelocity"):
        assert not is_rate_metric(key)


def test_statcast_full_names_mention_the_coverage_gap():
    for key in STATCAST_METRIC_KEYS:
        assert "Statcast" in full_name_for_metric(key) and "2015" in full_name_for_metric(key)
