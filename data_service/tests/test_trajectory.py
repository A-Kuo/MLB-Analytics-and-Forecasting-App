from unittest.mock import patch

import pandas as pd

import trajectory


def _hitter_game_log_splits(n=15):
    return [
        {
            "date": f"2026-04-{i + 1:02d}",
            "opponent": {"name": f"Opp {i}"},
            "isHome": i % 2 == 0,
            "stat": {"ops": 0.700 + 0.005 * i, "avg": 0.250, "obp": 0.320, "slg": 0.400},
        }
        for i in range(n)
    ]


@patch("trajectory.statcast_client.get_batter_batted_balls", return_value=[])
@patch("trajectory.mlb_client.get_game_log")
def test_hitter_trajectory_shape_without_statcast(mock_get_game_log, mock_get_bbe):
    # Distinct player_id from the other hitter test below -- compute_hitter_trajectory
    # is TTL-cached by (player_id, season, metric), and reusing the same key across
    # tests would silently return the first test's cached payload.
    mock_get_game_log.return_value = _hitter_game_log_splits()
    payload = trajectory.compute_hitter_trajectory(101, 2026, "ops")
    assert len(payload["x_labels"]) == 15
    assert len(payload["y_actual"]) == len(payload["y_pred"]) == 15
    assert payload["ci_lower"] and payload["ci_upper"]
    assert "used_statcast" not in payload


@patch("trajectory.mlb_client.get_game_log", return_value=[])
def test_hitter_trajectory_empty_game_log_returns_empty_payload(mock_get_game_log):
    payload = trajectory.compute_hitter_trajectory(102, 2026, "ops")
    assert payload["x_labels"] == []
    assert payload["holdout_r2"] is None


def _pitcher_pitch_rows(n=60):
    descriptions = ["called_strike", "ball", "swinging_strike", "foul", "hit_into_play"]
    return [
        {
            "game_date": "2026-04-01",
            "at_bat_number": str(i // 4),
            "pitch_number": str(i % 4 + 1),
            "description": descriptions[i % len(descriptions)],
            "release_speed": str(94.0 + (i % 5)),
            "release_spin_rate": str(2200 + i),
        }
        for i in range(n)
    ]


@patch("trajectory.statcast_client.get_pitcher_pitches")
def test_pitcher_trajectory_uses_statcast_when_available(mock_get_pitches):
    mock_get_pitches.return_value = _pitcher_pitch_rows()
    payload = trajectory.compute_pitcher_trajectory(201, 2026)
    assert payload["used_statcast"] is True
    assert "CSW%" in payload["metric_label"]
    assert len(payload["x_labels"]) == 60


@patch("trajectory.mlb_client.get_game_log")
@patch("trajectory.statcast_client.get_pitcher_pitches", return_value=[])
def test_pitcher_trajectory_falls_back_when_statcast_empty(mock_get_pitches, mock_get_game_log):
    mock_get_game_log.return_value = [
        {"date": f"2026-04-{i + 1:02d}", "opponent": {"name": "Opp"}, "isHome": True, "stat": {"era": 3.5 + i * 0.1}}
        for i in range(10)
    ]
    payload = trajectory.compute_pitcher_trajectory(202, 2026, fallback_metric="era")
    assert payload["used_statcast"] is False
    assert payload["metric_label"] == "ERA"
    assert len(payload["x_labels"]) == 10


@patch("trajectory.mlb_client.get_schedule")
def test_team_trajectory_offense_and_defense(mock_get_schedule):
    mock_get_schedule.return_value = [
        {
            "status": {"abstractGameState": "Final"},
            "officialDate": f"2026-04-{i + 1:02d}",
            "teams": {
                "home": {"team": {"id": 147, "name": "Yankees"}},
                "away": {"team": {"id": 111, "name": "Red Sox"}},
            },
            "linescore": {"innings": [{"num": 1, "home": {"runs": 3}, "away": {"runs": 2}}]},
        }
        for i in range(12)
    ]
    offense = trajectory.compute_team_trajectory(147, 2026, "offense")
    defense = trajectory.compute_team_trajectory(147, 2026, "defense")
    assert len(offense["y_actual"]) == 12
    assert len(defense["y_actual"]) == 12
    assert offense["y_actual"][0] == 3.0
    assert defense["y_actual"][0] == 2.0
