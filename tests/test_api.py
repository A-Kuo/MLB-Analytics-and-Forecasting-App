from unittest.mock import patch

from fastapi.testclient import TestClient

from macroservice.api import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_list_teams_returns_all_thirty():
    resp = client.get("/teams")
    assert resp.status_code == 200
    assert len(resp.json()) == 30


def test_roster_unknown_team_returns_404():
    resp = client.get("/teams/999999/roster", params={"season": 2026})
    assert resp.status_code == 404


@patch("macroservice.api.teams.get_roster")
def test_roster_known_team_delegates_to_client(mock_get_roster):
    mock_get_roster.return_value = [{"id": 1, "name": "Test Player", "position": "P", "is_pitcher": True}]
    resp = client.get("/teams/147/roster", params={"season": 2026})
    assert resp.status_code == 200
    assert resp.json()[0]["name"] == "Test Player"
    mock_get_roster.assert_called_once_with(147, 2026)


@patch("macroservice.api.teams.get_schedule")
def test_schedule_known_team_delegates_to_client(mock_get_schedule):
    mock_get_schedule.return_value = [{"gamePk": 1}]
    resp = client.get("/teams/147/schedule", params={"season": 2026})
    assert resp.status_code == 200
    assert resp.json() == [{"gamePk": 1}]


def test_game_log_rejects_invalid_group():
    resp = client.get("/players/123/game-log", params={"season": 2026, "group": "bogus"})
    assert resp.status_code == 422


@patch("macroservice.api.players.get_game_log")
def test_game_log_valid_group(mock_get_game_log):
    mock_get_game_log.return_value = [{"date": "2026-04-01"}]
    resp = client.get("/players/123/game-log", params={"season": 2026, "group": "pitching"})
    assert resp.status_code == 200
    mock_get_game_log.assert_called_once_with(123, 2026, "pitching")


@patch("macroservice.api.statcast.get_pitcher_pitches")
def test_statcast_pitcher_endpoint(mock_get_pitches):
    mock_get_pitches.return_value = [{"pitch_type": "FF"}]
    resp = client.get("/statcast/pitcher/456", params={"season": 2026})
    assert resp.status_code == 200
    assert resp.json() == [{"pitch_type": "FF"}]


@patch("macroservice.api.news.get_headlines")
def test_news_endpoint(mock_get_headlines):
    mock_get_headlines.return_value = [{"title": "Test", "url": "https://example.com"}]
    resp = client.get("/news", params={"keywords": ["Yankees"]})
    assert resp.status_code == 200
    assert resp.json()[0]["title"] == "Test"
