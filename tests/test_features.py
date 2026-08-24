import pandas as pd

from utils.features import (
    CSW_ROLLING_WINDOW,
    build_hitter_feature_frame,
    build_pitcher_csw_frame,
    build_team_rolling_frame,
)


def _hitter_game_log(n=12):
    return pd.DataFrame(
        {
            "date": pd.date_range("2026-04-01", periods=n, freq="D"),
            "opponent": [f"Opp {i}" for i in range(n)],
            "is_home": [i % 2 == 0 for i in range(n)],
            "ops": [0.700 + 0.01 * i for i in range(n)],
        }
    )


def test_hitter_feature_frame_without_statcast_falls_back_to_zero_columns():
    frame = build_hitter_feature_frame(_hitter_game_log(), pd.DataFrame(), metric="ops")
    assert (frame["rolling_ev"] == 0.0).all()
    assert (frame["rolling_xba"] == 0.0).all()
    assert (frame["rolling_hard_hit"] == 0.0).all()
    assert "rolling_metric" in frame.columns
    assert len(frame) == 12


def test_hitter_feature_frame_appearance_num_is_sequential():
    frame = build_hitter_feature_frame(_hitter_game_log(), pd.DataFrame(), metric="ops")
    assert frame["appearance_num"].tolist() == list(range(12))


def _pitcher_pitches(n=60):
    descriptions = ["called_strike", "ball", "swinging_strike", "foul", "hit_into_play"]
    return pd.DataFrame(
        {
            "game_date": ["2026-04-01"] * n,
            "at_bat_number": [i // 4 for i in range(n)],
            "pitch_number": [i % 4 + 1 for i in range(n)],
            "description": [descriptions[i % len(descriptions)] for i in range(n)],
            "release_speed": [94.0 + (i % 5) for i in range(n)],
            "release_spin_rate": [2200 + i for i in range(n)],
        }
    )


def test_pitcher_csw_frame_flags_called_strikes_and_whiffs():
    frame = build_pitcher_csw_frame(_pitcher_pitches())
    assert frame["is_csw"].sum() == frame["description"].isin(["called_strike", "swinging_strike"]).sum()
    assert frame["rolling_csw"].between(0, 1).all()
    assert frame["pitch_index"].tolist() == list(range(len(frame)))


def test_pitcher_csw_frame_rolling_window_bounded():
    frame = build_pitcher_csw_frame(_pitcher_pitches(n=CSW_ROLLING_WINDOW * 3))
    assert frame["rolling_whiff"].between(0, 1).all()


def test_team_rolling_frame_computes_offense_and_defense():
    schedule = pd.DataFrame(
        {
            "date": pd.date_range("2026-04-01", periods=15, freq="D"),
            "team_total_runs": [3, 5, 2, 4, 6, 1, 7, 3, 2, 5, 4, 6, 3, 2, 8],
            "opp_total_runs": [2, 1, 3, 4, 2, 5, 1, 3, 4, 2, 3, 1, 2, 4, 3],
        }
    )
    frame = build_team_rolling_frame(schedule, window=10)
    assert frame["game_num"].tolist() == list(range(15))
    assert frame["rolling_runs_for"].iloc[9] == sum(schedule["team_total_runs"][:10]) / 10
    assert frame["rolling_runs_against"].iloc[9] == sum(schedule["opp_total_runs"][:10]) / 10
