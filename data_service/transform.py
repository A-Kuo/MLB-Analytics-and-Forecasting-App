"""Converts raw clients/ JSON (MLB Stats API splits, Statcast CSV rows) into
the typed DataFrames that features.py and regression.py expect.
"""
from __future__ import annotations

import pandas as pd

RATE_STAT_COLUMNS = ("avg", "obp", "slg", "ops", "era", "whip")


def game_log_dataframe(splits: list[dict]) -> pd.DataFrame:
    """Per-game log from MLB Stats API gameLog splits, sorted chronologically."""
    rows = []
    for split in splits:
        row = {
            "date": split.get("date"),
            "opponent": split.get("opponent", {}).get("name", ""),
            "is_home": split.get("isHome", False),
        }
        row.update(split.get("stat", {}))
        rows.append(row)

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    for col in RATE_STAT_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def schedule_dataframe(games: list[dict], team_id: int) -> pd.DataFrame:
    """Completed games for a team, with total runs for and against, sorted chronologically."""
    rows = []
    for game in games:
        if game.get("status", {}).get("abstractGameState") != "Final":
            continue
        innings = (game.get("linescore") or {}).get("innings") or []
        if not innings:
            continue

        teams = game.get("teams", {})
        is_home = teams.get("home", {}).get("team", {}).get("id") == team_id
        side, opp_side = ("home", "away") if is_home else ("away", "home")

        team_runs = sum((i.get(side) or {}).get("runs") or 0 for i in innings)
        opp_runs = sum((i.get(opp_side) or {}).get("runs") or 0 for i in innings)

        rows.append(
            {
                "date": game.get("officialDate"),
                "opponent": teams.get(opp_side, {}).get("team", {}).get("name", ""),
                "is_home": is_home,
                "team_total_runs": team_runs,
                "opp_total_runs": opp_runs,
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)


def batted_balls_dataframe(rows: list[dict]) -> pd.DataFrame:
    """Statcast batted-ball CSV rows with numeric columns coerced."""
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    for col in ("launch_speed", "estimated_ba_using_speedangle"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def pitches_dataframe(rows: list[dict]) -> pd.DataFrame:
    """Statcast pitch-level CSV rows, untyped -- features.py coerces what it needs."""
    return pd.DataFrame(rows)
