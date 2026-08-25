import pytest

from macroservice import teams


def test_teams_has_all_thirty():
    assert len(teams.TEAMS) == 30


def test_team_by_id_matches_teams_list():
    assert set(teams.TEAM_BY_ID) == {team["id"] for team in teams.TEAMS}


def test_require_known_team_passes_for_known_id():
    known_id = teams.TEAMS[0]["id"]
    teams.require_known_team(known_id)  # should not raise


def test_require_known_team_raises_for_unknown_id():
    with pytest.raises(teams.UnknownTeamError):
        teams.require_known_team(999999)
