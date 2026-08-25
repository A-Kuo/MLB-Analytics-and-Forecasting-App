from unittest.mock import patch

from macroservice import players


def test_headshot_url_includes_player_id():
    url = players.headshot_url(682998)
    assert "/people/682998/headshot/67/current" in url


def test_headshot_url_default_width():
    url = players.headshot_url(682998)
    assert "w_213," in url


def test_headshot_url_custom_width():
    url = players.headshot_url(682998, width=120)
    assert "w_120," in url


def test_headshot_url_always_returns_a_string_even_for_unknown_id():
    # No network call happens here -- it's a pure URL template, so any int
    # produces a well-formed URL (the CDN's own fallback segment handles
    # unknown ids by serving a generic silhouette instead of erroring).
    url = players.headshot_url(999999999)
    assert url.startswith("https://img.mlbstatic.com/")


@patch("macroservice.players.get_season_stats")
def test_season_series_pulls_one_value_per_year(mock_get_season_stats):
    mock_get_season_stats.side_effect = lambda player_id, year, group: {"ops": 0.700 + 0.01 * (year - 2020)}
    series = players.get_season_series(1, "ops", "hitting", 2020, 2023)
    assert series["years"] == [2020, 2021, 2022, 2023]
    assert series["values"] == [0.700, 0.710, 0.720, 0.730]


@patch("macroservice.players.get_season_stats")
def test_season_series_skips_years_with_missing_metric(mock_get_season_stats):
    def fake_stats(player_id, year, group):
        return {} if year == 2021 else {"ops": 0.750}

    mock_get_season_stats.side_effect = fake_stats
    series = players.get_season_series(1, "ops", "hitting", 2020, 2022)
    assert series["years"] == [2020, 2022]
    assert series["values"] == [0.750, 0.750]


@patch("macroservice.players.get_season_stats")
def test_season_series_skips_non_numeric_metric_values(mock_get_season_stats):
    mock_get_season_stats.return_value = {"ops": "--"}
    series = players.get_season_series(1, "ops", "hitting", 2020, 2020)
    assert series == {"years": [], "values": []}


@patch("macroservice.players.get_season_stats")
def test_season_series_single_year_range(mock_get_season_stats):
    mock_get_season_stats.return_value = {"era": 3.14}
    series = players.get_season_series(1, "era", "pitching", 2022, 2022)
    assert series == {"years": [2022], "values": [3.14]}
