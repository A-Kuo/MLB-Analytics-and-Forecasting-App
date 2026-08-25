from unittest.mock import patch

import pytest

from macroservice import teams


def test_teams_has_all_thirty():
    assert len(teams.TEAMS) == 30


def test_every_team_has_a_verified_news_hub_slug():
    assert set(teams.TEAM_NEWS_HUB_SLUGS) == {team["id"] for team in teams.TEAMS}


def test_team_news_hub_url_uses_the_team_specific_slug():
    assert teams.team_news_hub_url(109) == "https://www.mlb.com/dbacks/news"


def test_team_news_hub_url_falls_back_to_general_hub_for_unknown_team():
    assert teams.team_news_hub_url(999999) == teams.GENERAL_NEWS_HUB_URL


def test_team_by_id_matches_teams_list():
    assert set(teams.TEAM_BY_ID) == {team["id"] for team in teams.TEAMS}


def test_require_known_team_passes_for_known_id():
    known_id = teams.TEAMS[0]["id"]
    teams.require_known_team(known_id)  # should not raise


def test_require_known_team_raises_for_unknown_id():
    with pytest.raises(teams.UnknownTeamError):
        teams.require_known_team(999999)


@patch("macroservice.teams.get_team_season_stats")
def test_team_season_series_pulls_one_value_per_year(mock_get_team_stats):
    mock_get_team_stats.side_effect = lambda team_id, year, group: {"ops": 0.700 + 0.01 * (year - 2020)}
    series = teams.get_team_season_series(147, "ops", "hitting", 2020, 2023)
    assert series["years"] == [2020, 2021, 2022, 2023]
    assert series["values"] == [0.700, 0.710, 0.720, 0.730]


@patch("macroservice.teams.get_team_season_stats")
def test_team_season_series_skips_years_with_missing_metric(mock_get_team_stats):
    def fake_stats(team_id, year, group):
        return {} if year == 2021 else {"ops": 0.750}

    mock_get_team_stats.side_effect = fake_stats
    series = teams.get_team_season_series(147, "ops", "hitting", 2020, 2022)
    assert series["years"] == [2020, 2022]
    assert series["values"] == [0.750, 0.750]
