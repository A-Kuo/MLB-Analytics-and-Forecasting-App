from utils.aggregation import aggregate_scalar, aggregate_series


def _series(years, values):
    return {"years": years, "values": values}


def test_aggregate_series_sums_counting_stats_per_year():
    series_by_player = {
        1: _series([2020, 2021], [10, 20]),
        2: _series([2020, 2021], [5, 15]),
    }
    result = aggregate_series(series_by_player, is_rate=False)
    assert result == {"years": [2020, 2021], "values": [15, 35]}


def test_aggregate_series_means_rate_stats_per_year():
    series_by_player = {
        1: _series([2020], [0.300]),
        2: _series([2020], [0.200]),
    }
    result = aggregate_series(series_by_player, is_rate=True)
    assert result["years"] == [2020]
    assert round(result["values"][0], 3) == 0.250


def test_aggregate_series_player_missing_a_year_does_not_block_it():
    # Player 2 has no 2021 data (outside their active span) -- that year's
    # aggregate should still be computed from whoever does have data.
    series_by_player = {
        1: _series([2020, 2021], [10, 20]),
        2: _series([2020], [5]),
    }
    result = aggregate_series(series_by_player, is_rate=False)
    assert result == {"years": [2020, 2021], "values": [15, 20]}


def test_aggregate_series_empty_input_returns_empty():
    assert aggregate_series({}, is_rate=False) == {"years": [], "values": []}


def test_aggregate_series_single_player_matches_their_own_series():
    series_by_player = {1: _series([2020, 2021], [0.3, 0.4])}
    result = aggregate_series(series_by_player, is_rate=True)
    assert result == {"years": [2020, 2021], "values": [0.3, 0.4]}


def test_aggregate_scalar_sums_counting_stats_across_everything():
    series_by_player = {
        1: _series([2020, 2021], [10, 20]),
        2: _series([2020], [5]),
    }
    assert aggregate_scalar(series_by_player, is_rate=False) == 35


def test_aggregate_scalar_means_rate_stats_across_everything():
    series_by_player = {
        1: _series([2020, 2021], [0.300, 0.400]),
        2: _series([2020], [0.200]),
    }
    # (0.300 + 0.400 + 0.200) / 3
    assert round(aggregate_scalar(series_by_player, is_rate=True), 4) == round(0.9 / 3, 4)


def test_aggregate_scalar_returns_none_when_no_data():
    assert aggregate_scalar({1: _series([], [])}, is_rate=False) is None
    assert aggregate_scalar({}, is_rate=True) is None
