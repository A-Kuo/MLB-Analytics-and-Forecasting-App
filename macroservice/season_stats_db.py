"""Postgres-backed storage for player/team season stats, Statcast season
aggregates, and player game logs.

Same shape as macroservice/roster_history_db.py -- every function takes an
already-open SQLAlchemy Engine, Streamlit-free, so the same code serves
client.py (via st.connection) and any standalone script. See client.py for
the freshness-split logic (only completed seasons get cached at all; the
current season always goes straight to the live API).

Each scalar fetch_* (season stats, Statcast season, team stats) returns
``None`` on a genuine cache miss and a real dict -- even one full of
``None`` values -- once a row has actually been written, so "confirmed:
this player has no pitching stats this season" is distinguishable from
"never checked." That distinction relies on a row always being written on
upsert, even for an empty API result.

The two game-log fetch_* functions can't cheaply make that same
distinction without a separate marker row (a whole season can legitimately
have zero games, e.g. a season-ending injury) -- they return ``[]`` for
both "not cached" and "confirmed empty," the same accepted imprecision
macroservice/roster_history_db.py's fetch_team_roster_rows already carries
for a different reason. Worst case: a genuinely gameless season gets
re-fetched from the live API every time it's requested -- harmless, just
not maximally efficient.

Dict keys returned by the scalar fetches match the live API's own field
names (``avg``, ``homeRuns``, ...), not the tables' snake_case columns, so
client.py's cached and live paths are interchangeable to every caller.
"""
from __future__ import annotations

from sqlalchemy import Engine, text


def _to_float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Player season stats (plain MLB Stats API)
# ---------------------------------------------------------------------------

_FETCH_PLAYER_SEASON_HITTING_SQL = text(
    "SELECT avg, obp, slg, ops, home_runs, rbi, strikeouts, walks "
    "FROM player_season_hitting_stats WHERE player_id = :player_id AND season = :season"
)
_UPSERT_PLAYER_SEASON_HITTING_SQL = text("""
    INSERT INTO player_season_hitting_stats
        (player_id, season, avg, obp, slg, ops, home_runs, rbi, strikeouts, walks)
    VALUES
        (:player_id, :season, :avg, :obp, :slg, :ops, :home_runs, :rbi, :strikeouts, :walks)
    ON CONFLICT (player_id, season) DO UPDATE SET
        avg = EXCLUDED.avg, obp = EXCLUDED.obp, slg = EXCLUDED.slg, ops = EXCLUDED.ops,
        home_runs = EXCLUDED.home_runs, rbi = EXCLUDED.rbi,
        strikeouts = EXCLUDED.strikeouts, walks = EXCLUDED.walks
""")

_FETCH_PLAYER_SEASON_PITCHING_SQL = text(
    "SELECT era, whip, strikeouts, walks, innings_pitched, earned_runs "
    "FROM player_season_pitching_stats WHERE player_id = :player_id AND season = :season"
)
_UPSERT_PLAYER_SEASON_PITCHING_SQL = text("""
    INSERT INTO player_season_pitching_stats
        (player_id, season, era, whip, strikeouts, walks, innings_pitched, earned_runs)
    VALUES
        (:player_id, :season, :era, :whip, :strikeouts, :walks, :innings_pitched, :earned_runs)
    ON CONFLICT (player_id, season) DO UPDATE SET
        era = EXCLUDED.era, whip = EXCLUDED.whip, strikeouts = EXCLUDED.strikeouts,
        walks = EXCLUDED.walks, innings_pitched = EXCLUDED.innings_pitched,
        earned_runs = EXCLUDED.earned_runs
""")


def fetch_player_season_hitting(engine: Engine, player_id: int, season: int) -> dict | None:
    with engine.connect() as conn:
        row = conn.execute(_FETCH_PLAYER_SEASON_HITTING_SQL, {"player_id": player_id, "season": season}).mappings().first()
    if row is None:
        return None
    return {
        "avg": row["avg"], "obp": row["obp"], "slg": row["slg"], "ops": row["ops"],
        "homeRuns": row["home_runs"], "rbi": row["rbi"], "strikeOuts": row["strikeouts"], "baseOnBalls": row["walks"],
    }


def upsert_player_season_hitting(engine: Engine, player_id: int, season: int, stats: dict) -> None:
    """``stats``: the raw dict from players.get_season_stats(..., "hitting")
    -- writes a row even when ``stats`` is ``{}`` (a real "no data" API
    result), so that outcome is cached too, not re-fetched every time.
    """
    params = {
        "player_id": player_id, "season": season,
        "avg": _to_float(stats.get("avg")), "obp": _to_float(stats.get("obp")),
        "slg": _to_float(stats.get("slg")), "ops": _to_float(stats.get("ops")),
        "home_runs": _to_int(stats.get("homeRuns")), "rbi": _to_int(stats.get("rbi")),
        "strikeouts": _to_int(stats.get("strikeOuts")), "walks": _to_int(stats.get("baseOnBalls")),
    }
    with engine.begin() as conn:
        conn.execute(_UPSERT_PLAYER_SEASON_HITTING_SQL, params)


def fetch_player_season_pitching(engine: Engine, player_id: int, season: int) -> dict | None:
    with engine.connect() as conn:
        row = conn.execute(_FETCH_PLAYER_SEASON_PITCHING_SQL, {"player_id": player_id, "season": season}).mappings().first()
    if row is None:
        return None
    return {
        "era": row["era"], "whip": row["whip"], "strikeOuts": row["strikeouts"], "baseOnBalls": row["walks"],
        "inningsPitched": row["innings_pitched"], "earnedRuns": row["earned_runs"],
    }


def upsert_player_season_pitching(engine: Engine, player_id: int, season: int, stats: dict) -> None:
    params = {
        "player_id": player_id, "season": season,
        "era": _to_float(stats.get("era")), "whip": _to_float(stats.get("whip")),
        "strikeouts": _to_int(stats.get("strikeOuts")), "walks": _to_int(stats.get("baseOnBalls")),
        # Stored as float(raw) -- the API's "182.1" thirds-notation (182 and
        # 1/3 innings) already gets parsed as naive decimal by the live path
        # (players.get_season_series), so this preserves that existing
        # behavior rather than fixing an unrelated pre-existing quirk here.
        "innings_pitched": _to_float(stats.get("inningsPitched")),
        "earned_runs": _to_int(stats.get("earnedRuns")),
    }
    with engine.begin() as conn:
        conn.execute(_UPSERT_PLAYER_SEASON_PITCHING_SQL, params)


# ---------------------------------------------------------------------------
# Player Statcast season aggregates (2015+ only)
# ---------------------------------------------------------------------------

_FETCH_PLAYER_STATCAST_HITTING_SQL = text(
    "SELECT xba, avg_exit_velocity, hard_hit_pct, barrel_pct "
    "FROM player_statcast_hitting_season WHERE player_id = :player_id AND season = :season"
)
_UPSERT_PLAYER_STATCAST_HITTING_SQL = text("""
    INSERT INTO player_statcast_hitting_season (player_id, season, xba, avg_exit_velocity, hard_hit_pct, barrel_pct)
    VALUES (:player_id, :season, :xba, :avg_exit_velocity, :hard_hit_pct, :barrel_pct)
    ON CONFLICT (player_id, season) DO UPDATE SET
        xba = EXCLUDED.xba, avg_exit_velocity = EXCLUDED.avg_exit_velocity,
        hard_hit_pct = EXCLUDED.hard_hit_pct, barrel_pct = EXCLUDED.barrel_pct
""")

_FETCH_PLAYER_STATCAST_PITCHING_SQL = text(
    "SELECT csw_pct, whiff_pct, chase_pct, avg_velocity "
    "FROM player_statcast_pitching_season WHERE player_id = :player_id AND season = :season"
)
_UPSERT_PLAYER_STATCAST_PITCHING_SQL = text("""
    INSERT INTO player_statcast_pitching_season (player_id, season, csw_pct, whiff_pct, chase_pct, avg_velocity)
    VALUES (:player_id, :season, :csw_pct, :whiff_pct, :chase_pct, :avg_velocity)
    ON CONFLICT (player_id, season) DO UPDATE SET
        csw_pct = EXCLUDED.csw_pct, whiff_pct = EXCLUDED.whiff_pct,
        chase_pct = EXCLUDED.chase_pct, avg_velocity = EXCLUDED.avg_velocity
""")


def fetch_player_statcast_hitting_season(engine: Engine, player_id: int, season: int) -> dict | None:
    with engine.connect() as conn:
        row = conn.execute(_FETCH_PLAYER_STATCAST_HITTING_SQL, {"player_id": player_id, "season": season}).mappings().first()
    if row is None:
        return None
    return {"xba": row["xba"], "avgExitVelocity": row["avg_exit_velocity"], "hardHitPct": row["hard_hit_pct"], "barrelPct": row["barrel_pct"]}


def upsert_player_statcast_hitting_season(engine: Engine, player_id: int, season: int, stats: dict) -> None:
    params = {
        "player_id": player_id, "season": season,
        "xba": _to_float(stats.get("xba")), "avg_exit_velocity": _to_float(stats.get("avgExitVelocity")),
        "hard_hit_pct": _to_float(stats.get("hardHitPct")), "barrel_pct": _to_float(stats.get("barrelPct")),
    }
    with engine.begin() as conn:
        conn.execute(_UPSERT_PLAYER_STATCAST_HITTING_SQL, params)


def fetch_player_statcast_pitching_season(engine: Engine, player_id: int, season: int) -> dict | None:
    with engine.connect() as conn:
        row = conn.execute(_FETCH_PLAYER_STATCAST_PITCHING_SQL, {"player_id": player_id, "season": season}).mappings().first()
    if row is None:
        return None
    return {"cswPct": row["csw_pct"], "whiffPct": row["whiff_pct"], "chasePct": row["chase_pct"], "avgVelocity": row["avg_velocity"]}


def upsert_player_statcast_pitching_season(engine: Engine, player_id: int, season: int, stats: dict) -> None:
    params = {
        "player_id": player_id, "season": season,
        "csw_pct": _to_float(stats.get("cswPct")), "whiff_pct": _to_float(stats.get("whiffPct")),
        "chase_pct": _to_float(stats.get("chasePct")), "avg_velocity": _to_float(stats.get("avgVelocity")),
    }
    with engine.begin() as conn:
        conn.execute(_UPSERT_PLAYER_STATCAST_PITCHING_SQL, params)


# ---------------------------------------------------------------------------
# Player game logs
# ---------------------------------------------------------------------------

_FETCH_PLAYER_GAME_LOG_HITTING_SQL = text("""
    SELECT game_date, opponent, at_bats, hits, home_runs, rbi, walks, strikeouts, avg
    FROM player_game_log_hitting WHERE player_id = :player_id AND season = :season
    ORDER BY game_date, game_index
""")
_UPSERT_PLAYER_GAME_LOG_HITTING_SQL = text("""
    INSERT INTO player_game_log_hitting
        (player_id, season, game_date, game_index, opponent, at_bats, hits, home_runs, rbi, walks, strikeouts, avg)
    VALUES
        (:player_id, :season, :game_date, :game_index, :opponent, :at_bats, :hits, :home_runs, :rbi, :walks, :strikeouts, :avg)
    ON CONFLICT (player_id, season, game_date, game_index) DO UPDATE SET
        opponent = EXCLUDED.opponent, at_bats = EXCLUDED.at_bats, hits = EXCLUDED.hits,
        home_runs = EXCLUDED.home_runs, rbi = EXCLUDED.rbi, walks = EXCLUDED.walks,
        strikeouts = EXCLUDED.strikeouts, avg = EXCLUDED.avg
""")

_FETCH_PLAYER_GAME_LOG_PITCHING_SQL = text("""
    SELECT game_date, opponent, innings_pitched, hits, earned_runs, strikeouts, walks, era
    FROM player_game_log_pitching WHERE player_id = :player_id AND season = :season
    ORDER BY game_date, game_index
""")
_UPSERT_PLAYER_GAME_LOG_PITCHING_SQL = text("""
    INSERT INTO player_game_log_pitching
        (player_id, season, game_date, game_index, opponent, innings_pitched, hits, earned_runs, strikeouts, walks, era)
    VALUES
        (:player_id, :season, :game_date, :game_index, :opponent, :innings_pitched, :hits, :earned_runs, :strikeouts, :walks, :era)
    ON CONFLICT (player_id, season, game_date, game_index) DO UPDATE SET
        opponent = EXCLUDED.opponent, innings_pitched = EXCLUDED.innings_pitched, hits = EXCLUDED.hits,
        earned_runs = EXCLUDED.earned_runs, strikeouts = EXCLUDED.strikeouts, walks = EXCLUDED.walks, era = EXCLUDED.era
""")


def _dedupe_game_index(splits: list[dict]) -> list[int]:
    """0 for the first game on a given date, 1 for a doubleheader nightcap,
    etc. -- the fallback disambiguator when a split has no other unique
    per-game id (see db/schema.sql's comment on this pair of tables for
    the "verify against a real gamePk-style field" follow-up).
    """
    seen: dict[str, int] = {}
    indices = []
    for split in splits:
        date = split.get("date")
        indices.append(seen.get(date, 0))
        seen[date] = seen.get(date, 0) + 1
    return indices


def fetch_player_game_log_hitting(engine: Engine, player_id: int, season: int) -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(_FETCH_PLAYER_GAME_LOG_HITTING_SQL, {"player_id": player_id, "season": season}).mappings().all()
    return [
        {
            "date": str(row["game_date"]), "opponent": {"name": row["opponent"]},
            "stat": {"atBats": row["at_bats"], "hits": row["hits"], "homeRuns": row["home_runs"], "rbi": row["rbi"],
                      "baseOnBalls": row["walks"], "strikeOuts": row["strikeouts"], "avg": row["avg"]},
        }
        for row in rows
    ]


def upsert_player_game_log_hitting(engine: Engine, player_id: int, season: int, splits: list[dict]) -> None:
    """``splits``: the raw list from players.get_game_log(..., "hitting").
    A no-op for an empty list -- see the module docstring on why an empty
    season isn't distinguishable from "not cached" here.
    """
    if not splits:
        return
    indices = _dedupe_game_index(splits)
    params = [
        {
            "player_id": player_id, "season": season, "game_date": split.get("date"), "game_index": idx,
            "opponent": (split.get("opponent") or {}).get("name"),
            "at_bats": _to_int((split.get("stat") or {}).get("atBats")),
            "hits": _to_int((split.get("stat") or {}).get("hits")),
            "home_runs": _to_int((split.get("stat") or {}).get("homeRuns")),
            "rbi": _to_int((split.get("stat") or {}).get("rbi")),
            "walks": _to_int((split.get("stat") or {}).get("baseOnBalls")),
            "strikeouts": _to_int((split.get("stat") or {}).get("strikeOuts")),
            "avg": _to_float((split.get("stat") or {}).get("avg")),
        }
        for split, idx in zip(splits, indices)
    ]
    with engine.begin() as conn:
        conn.execute(_UPSERT_PLAYER_GAME_LOG_HITTING_SQL, params)


def fetch_player_game_log_pitching(engine: Engine, player_id: int, season: int) -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(_FETCH_PLAYER_GAME_LOG_PITCHING_SQL, {"player_id": player_id, "season": season}).mappings().all()
    return [
        {
            "date": str(row["game_date"]), "opponent": {"name": row["opponent"]},
            "stat": {"inningsPitched": row["innings_pitched"], "hits": row["hits"], "earnedRuns": row["earned_runs"],
                      "strikeOuts": row["strikeouts"], "baseOnBalls": row["walks"], "era": row["era"]},
        }
        for row in rows
    ]


def upsert_player_game_log_pitching(engine: Engine, player_id: int, season: int, splits: list[dict]) -> None:
    if not splits:
        return
    indices = _dedupe_game_index(splits)
    params = [
        {
            "player_id": player_id, "season": season, "game_date": split.get("date"), "game_index": idx,
            "opponent": (split.get("opponent") or {}).get("name"),
            "innings_pitched": _to_float((split.get("stat") or {}).get("inningsPitched")),
            "hits": _to_int((split.get("stat") or {}).get("hits")),
            "earned_runs": _to_int((split.get("stat") or {}).get("earnedRuns")),
            "strikeouts": _to_int((split.get("stat") or {}).get("strikeOuts")),
            "walks": _to_int((split.get("stat") or {}).get("baseOnBalls")),
            "era": _to_float((split.get("stat") or {}).get("era")),
        }
        for split, idx in zip(splits, indices)
    ]
    with engine.begin() as conn:
        conn.execute(_UPSERT_PLAYER_GAME_LOG_PITCHING_SQL, params)


# ---------------------------------------------------------------------------
# Team season stats
# ---------------------------------------------------------------------------

_FETCH_TEAM_SEASON_HITTING_SQL = text(
    "SELECT runs, avg, obp, slg, ops, games_played "
    "FROM team_season_hitting_stats WHERE team_id = :team_id AND season = :season"
)
_UPSERT_TEAM_SEASON_HITTING_SQL = text("""
    INSERT INTO team_season_hitting_stats (team_id, season, runs, avg, obp, slg, ops, games_played)
    VALUES (:team_id, :season, :runs, :avg, :obp, :slg, :ops, :games_played)
    ON CONFLICT (team_id, season) DO UPDATE SET
        runs = EXCLUDED.runs, avg = EXCLUDED.avg, obp = EXCLUDED.obp, slg = EXCLUDED.slg,
        ops = EXCLUDED.ops, games_played = EXCLUDED.games_played
""")

_FETCH_TEAM_SEASON_PITCHING_SQL = text(
    "SELECT wins, losses, runs_allowed, era, whip, games_played "
    "FROM team_season_pitching_stats WHERE team_id = :team_id AND season = :season"
)
_UPSERT_TEAM_SEASON_PITCHING_SQL = text("""
    INSERT INTO team_season_pitching_stats (team_id, season, wins, losses, runs_allowed, era, whip, games_played)
    VALUES (:team_id, :season, :wins, :losses, :runs_allowed, :era, :whip, :games_played)
    ON CONFLICT (team_id, season) DO UPDATE SET
        wins = EXCLUDED.wins, losses = EXCLUDED.losses, runs_allowed = EXCLUDED.runs_allowed,
        era = EXCLUDED.era, whip = EXCLUDED.whip, games_played = EXCLUDED.games_played
""")


def fetch_team_season_hitting(engine: Engine, team_id: int, season: int) -> dict | None:
    with engine.connect() as conn:
        row = conn.execute(_FETCH_TEAM_SEASON_HITTING_SQL, {"team_id": team_id, "season": season}).mappings().first()
    if row is None:
        return None
    return {"runs": row["runs"], "avg": row["avg"], "obp": row["obp"], "slg": row["slg"], "ops": row["ops"], "gamesPlayed": row["games_played"]}


def upsert_team_season_hitting(engine: Engine, team_id: int, season: int, stats: dict) -> None:
    params = {
        "team_id": team_id, "season": season,
        "runs": _to_int(stats.get("runs")), "avg": _to_float(stats.get("avg")),
        "obp": _to_float(stats.get("obp")), "slg": _to_float(stats.get("slg")),
        "ops": _to_float(stats.get("ops")), "games_played": _to_int(stats.get("gamesPlayed")),
    }
    with engine.begin() as conn:
        conn.execute(_UPSERT_TEAM_SEASON_HITTING_SQL, params)


def fetch_team_season_pitching(engine: Engine, team_id: int, season: int) -> dict | None:
    with engine.connect() as conn:
        row = conn.execute(_FETCH_TEAM_SEASON_PITCHING_SQL, {"team_id": team_id, "season": season}).mappings().first()
    if row is None:
        return None
    return {"wins": row["wins"], "losses": row["losses"], "runs": row["runs_allowed"], "era": row["era"], "whip": row["whip"], "gamesPlayed": row["games_played"]}


def upsert_team_season_pitching(engine: Engine, team_id: int, season: int, stats: dict) -> None:
    params = {
        "team_id": team_id, "season": season,
        "wins": _to_int(stats.get("wins")), "losses": _to_int(stats.get("losses")),
        "runs_allowed": _to_int(stats.get("runs")), "era": _to_float(stats.get("era")),
        "whip": _to_float(stats.get("whip")), "games_played": _to_int(stats.get("gamesPlayed")),
    }
    with engine.begin() as conn:
        conn.execute(_UPSERT_TEAM_SEASON_PITCHING_SQL, params)
