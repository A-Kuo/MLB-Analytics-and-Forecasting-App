"""Feature engineering for the hitter/pitcher/team trajectory models.

Builds the multivariate feature matrices consumed by
``regression.fit_trajectory_ensemble``. Takes DataFrames already assembled
by ``transform.py`` from the raw clients/ JSON responses.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

HITTER_ROLLING_WINDOW = 10       # appearances -- offensive trajectory engine
PITCHER_ROLLING_WINDOW = 5       # appearances -- legacy ERA/WHIP fallback window
CSW_ROLLING_WINDOW = 25          # pitches -- defensive (CSW%) trajectory engine
MOMENTUM_WINDOW_HITTER = 3
MOMENTUM_WINDOW_PITCHER_PITCHES = 5

# Statcast `description` values that count as a swing, a whiff, and a called
# strike + whiff (CSW), respectively.
SWING_DESCRIPTIONS = {
    "foul", "foul_tip", "foul_bunt", "hit_into_play",
    "swinging_strike", "swinging_strike_blocked", "missed_bunt",
}
WHIFF_DESCRIPTIONS = {"swinging_strike", "swinging_strike_blocked", "missed_bunt"}
CSW_DESCRIPTIONS = {"called_strike"} | WHIFF_DESCRIPTIONS

HITTER_FEATURE_COLUMNS = [
    "appearance_num", "momentum_3", "is_home", "rest_days",
    "rolling_ev", "rolling_xba", "rolling_hard_hit",
]
PITCHER_FEATURE_COLUMNS = ["pitch_index", "momentum_csw_5", "rolling_whiff", "rolling_velo", "rolling_spin"]


def build_hitter_feature_frame(game_log: pd.DataFrame, batted_balls: pd.DataFrame, metric: str = "ops") -> pd.DataFrame:
    """One row per game: [appearance_num, momentum_3, is_home, rest_days,
    rolling_ev, rolling_xba, rolling_hard_hit] plus ``rolling_metric`` (the
    10-appearance rolling average of ``metric`` -- the regression target).

    Falls back gracefully when Statcast batted-ball data is unavailable: the
    rolling_ev/xba/hard_hit columns become a constant (0.0), which the model
    can still fit around using the MLB Stats API-derived features alone.
    """
    df = game_log.sort_values("date").reset_index(drop=True).copy()
    df["appearance_num"] = np.arange(len(df))
    df["is_home"] = df["is_home"].astype(int) if "is_home" in df.columns else 0
    df["rest_days"] = df["date"].diff().dt.days.fillna(0)
    df["momentum_3"] = df[metric].rolling(MOMENTUM_WINDOW_HITTER, min_periods=1).mean()
    df["rolling_metric"] = df[metric].rolling(HITTER_ROLLING_WINDOW, min_periods=1).mean()

    if batted_balls is not None and not batted_balls.empty and "game_date" in batted_balls.columns:
        daily = (
            batted_balls.assign(date=pd.to_datetime(batted_balls["game_date"]))
            .groupby("date")
            .agg(
                ev=("launch_speed", "mean"),
                xba=("estimated_ba_using_speedangle", "mean"),
                hard_hit=("launch_speed", lambda s: float((s >= 95).mean())),
            )
            .reset_index()
        )
        df = df.merge(daily, on="date", how="left")
    else:
        df["ev"] = df["xba"] = df["hard_hit"] = np.nan

    df["rolling_ev"] = df["ev"].rolling(HITTER_ROLLING_WINDOW, min_periods=1).mean()
    df["rolling_xba"] = df["xba"].rolling(HITTER_ROLLING_WINDOW, min_periods=1).mean()
    df["rolling_hard_hit"] = df["hard_hit"].rolling(HITTER_ROLLING_WINDOW, min_periods=1).mean()
    for col in ("rolling_ev", "rolling_xba", "rolling_hard_hit"):
        df[col] = df[col].fillna(0.0)

    return df


def build_pitcher_csw_frame(pitches: pd.DataFrame) -> pd.DataFrame:
    """One pitch-level row per pitch, chronologically ordered, with the CSW%
    rolling target (25-pitch window) and [pitch_index, momentum_csw_5,
    rolling_whiff, rolling_velo, rolling_spin].
    """
    df = pitches.sort_values(["game_date", "at_bat_number", "pitch_number"]).reset_index(drop=True).copy()
    df["pitch_index"] = np.arange(len(df))
    df["is_csw"] = df["description"].isin(CSW_DESCRIPTIONS).astype(int)
    df["is_swing"] = df["description"].isin(SWING_DESCRIPTIONS).astype(int)
    df["is_whiff"] = df["description"].isin(WHIFF_DESCRIPTIONS).astype(int)

    df["rolling_csw"] = df["is_csw"].rolling(CSW_ROLLING_WINDOW, min_periods=1).mean()
    df["momentum_csw_5"] = df["is_csw"].rolling(MOMENTUM_WINDOW_PITCHER_PITCHES, min_periods=1).mean()

    swings = df["is_swing"].rolling(CSW_ROLLING_WINDOW, min_periods=1).sum()
    whiffs = df["is_whiff"].rolling(CSW_ROLLING_WINDOW, min_periods=1).sum()
    df["rolling_whiff"] = (whiffs / swings.replace(0, np.nan)).fillna(0.0)

    df["release_speed"] = pd.to_numeric(df.get("release_speed"), errors="coerce")
    df["release_spin_rate"] = pd.to_numeric(df.get("release_spin_rate"), errors="coerce")
    df["rolling_velo"] = df["release_speed"].rolling(CSW_ROLLING_WINDOW, min_periods=1).mean()
    df["rolling_spin"] = df["release_spin_rate"].rolling(CSW_ROLLING_WINDOW, min_periods=1).mean()
    velo_mean = df["release_speed"].mean()
    spin_mean = df["release_spin_rate"].mean()
    df["rolling_velo"] = df["rolling_velo"].fillna(velo_mean if pd.notna(velo_mean) else 0.0)
    df["rolling_spin"] = df["rolling_spin"].fillna(spin_mean if pd.notna(spin_mean) else 0.0)

    return df


def build_team_rolling_frame(schedule: pd.DataFrame, window: int = 10) -> pd.DataFrame:
    """One row per completed game with ``game_num`` and 10-game rolling
    runs-scored (offense) / runs-allowed (defense).
    """
    df = schedule.sort_values("date").reset_index(drop=True).copy()
    df["game_num"] = np.arange(len(df))
    df["rolling_runs_for"] = df["team_total_runs"].rolling(window, min_periods=1).mean()
    df["rolling_runs_against"] = df["opp_total_runs"].rolling(window, min_periods=1).mean()
    return df
