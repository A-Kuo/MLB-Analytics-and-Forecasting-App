from unittest.mock import patch

from macroservice import statcast_season


def _batted_ball(launch_speed=None, xba=None, lsa=None):
    row = {}
    if launch_speed is not None:
        row["launch_speed"] = str(launch_speed)
    if xba is not None:
        row["estimated_ba_using_speedangle"] = str(xba)
    if lsa is not None:
        row["launch_speed_angle"] = str(lsa)
    return row


def _pitch(description="ball", zone="5", release_speed=None):
    row = {"description": description, "zone": zone}
    if release_speed is not None:
        row["release_speed"] = str(release_speed)
    return row


# ---------------------------------------------------------------------------
# compute_hitter_statcast_season
# ---------------------------------------------------------------------------


def test_hitter_season_returns_all_none_before_statcast_era():
    result = statcast_season.compute_hitter_statcast_season(1, 2014)
    assert result == {"xba": None, "avgExitVelocity": None, "hardHitPct": None, "barrelPct": None}


@patch("macroservice.statcast_season.statcast.get_batter_batted_balls")
def test_hitter_season_returns_all_none_when_no_batted_balls(mock_get_bbe):
    mock_get_bbe.return_value = []
    result = statcast_season.compute_hitter_statcast_season(101, 2024)
    assert result == {"xba": None, "avgExitVelocity": None, "hardHitPct": None, "barrelPct": None}


@patch("macroservice.statcast_season.statcast.get_batter_batted_balls")
def test_hitter_season_computes_xba_and_exit_velocity_means(mock_get_bbe):
    mock_get_bbe.return_value = [
        _batted_ball(launch_speed=100, xba=0.800, lsa="6"),
        _batted_ball(launch_speed=80, xba=0.200, lsa="2"),
    ]
    result = statcast_season.compute_hitter_statcast_season(102, 2024)
    assert result["avgExitVelocity"] == 90.0
    assert round(result["xba"], 3) == 0.500


@patch("macroservice.statcast_season.statcast.get_batter_batted_balls")
def test_hitter_season_hard_hit_pct_uses_95mph_threshold(mock_get_bbe):
    mock_get_bbe.return_value = [
        _batted_ball(launch_speed=96),  # hard hit
        _batted_ball(launch_speed=94),  # not
        _batted_ball(launch_speed=95),  # exactly at threshold -- hard hit
        _batted_ball(launch_speed=50),  # not
    ]
    result = statcast_season.compute_hitter_statcast_season(103, 2024)
    assert result["hardHitPct"] == 0.5


@patch("macroservice.statcast_season.statcast.get_batter_batted_balls")
def test_hitter_season_barrel_pct_uses_official_launch_speed_angle_6(mock_get_bbe):
    mock_get_bbe.return_value = [
        _batted_ball(lsa="6"),
        _batted_ball(lsa="6"),
        _batted_ball(lsa="3"),
        _batted_ball(lsa="1"),
    ]
    result = statcast_season.compute_hitter_statcast_season(104, 2024)
    assert result["barrelPct"] == 0.5


# ---------------------------------------------------------------------------
# compute_pitcher_statcast_season
# ---------------------------------------------------------------------------


def test_pitcher_season_returns_all_none_before_statcast_era():
    result = statcast_season.compute_pitcher_statcast_season(1, 2010)
    assert result == {"cswPct": None, "whiffPct": None, "chasePct": None, "avgVelocity": None}


@patch("macroservice.statcast_season.statcast.get_pitcher_pitches")
def test_pitcher_season_returns_all_none_when_no_pitches(mock_get_pitches):
    mock_get_pitches.return_value = []
    result = statcast_season.compute_pitcher_statcast_season(201, 2024)
    assert result == {"cswPct": None, "whiffPct": None, "chasePct": None, "avgVelocity": None}


@patch("macroservice.statcast_season.statcast.get_pitcher_pitches")
def test_pitcher_season_csw_pct(mock_get_pitches):
    mock_get_pitches.return_value = [
        _pitch("called_strike"),
        _pitch("swinging_strike"),
        _pitch("ball"),
        _pitch("ball"),
    ]
    result = statcast_season.compute_pitcher_statcast_season(202, 2024)
    assert result["cswPct"] == 0.5


@patch("macroservice.statcast_season.statcast.get_pitcher_pitches")
def test_pitcher_season_whiff_pct_is_whiffs_over_swings(mock_get_pitches):
    mock_get_pitches.return_value = [
        _pitch("swinging_strike"),  # swing + whiff
        _pitch("foul"),  # swing, not whiff
        _pitch("ball"),  # not a swing
    ]
    result = statcast_season.compute_pitcher_statcast_season(203, 2024)
    assert result["whiffPct"] == 0.5


@patch("macroservice.statcast_season.statcast.get_pitcher_pitches")
def test_pitcher_season_whiff_pct_none_when_no_swings(mock_get_pitches):
    mock_get_pitches.return_value = [_pitch("ball"), _pitch("called_strike")]
    result = statcast_season.compute_pitcher_statcast_season(204, 2024)
    assert result["whiffPct"] is None


@patch("macroservice.statcast_season.statcast.get_pitcher_pitches")
def test_pitcher_season_chase_pct_is_out_of_zone_swings_over_out_of_zone_pitches(mock_get_pitches):
    mock_get_pitches.return_value = [
        _pitch("foul", zone="11"),  # out of zone, swing
        _pitch("ball", zone="12"),  # out of zone, no swing
        _pitch("called_strike", zone="5"),  # in zone -- excluded
    ]
    result = statcast_season.compute_pitcher_statcast_season(205, 2024)
    assert result["chasePct"] == 0.5


@patch("macroservice.statcast_season.statcast.get_pitcher_pitches")
def test_pitcher_season_avg_velocity(mock_get_pitches):
    mock_get_pitches.return_value = [_pitch(release_speed=90), _pitch(release_speed=94)]
    result = statcast_season.compute_pitcher_statcast_season(206, 2024)
    assert result["avgVelocity"] == 92.0


# ---------------------------------------------------------------------------
# get_hitter_statcast_series / get_pitcher_statcast_series
# ---------------------------------------------------------------------------


@patch("macroservice.statcast_season.compute_hitter_statcast_season")
def test_hitter_series_clamps_start_year_to_statcast_era(mock_compute):
    mock_compute.return_value = {"xba": 0.3, "avgExitVelocity": None, "hardHitPct": None, "barrelPct": None}
    series = statcast_season.get_hitter_statcast_series(301, "xba", 2010, 2016)
    # requested range starts in 2010, but only 2015/2016 should be queried
    queried_years = [call.args[1] for call in mock_compute.call_args_list]
    assert queried_years == [2015, 2016]
    assert series["years"] == [2015, 2016]


@patch("macroservice.statcast_season.compute_hitter_statcast_season")
def test_hitter_series_skips_years_with_no_data(mock_compute):
    def fake(player_id, year):
        return {"xba": None, "avgExitVelocity": None, "hardHitPct": None, "barrelPct": None} if year == 2016 else {
            "xba": 0.3, "avgExitVelocity": None, "hardHitPct": None, "barrelPct": None
        }

    mock_compute.side_effect = fake
    series = statcast_season.get_hitter_statcast_series(302, "xba", 2015, 2017)
    assert series["years"] == [2015, 2017]
    assert series["values"] == [0.3, 0.3]


@patch("macroservice.statcast_season.compute_pitcher_statcast_season")
def test_pitcher_series_skips_years_with_no_data(mock_compute):
    def fake(player_id, year):
        return {"cswPct": None} if year == 2020 else {"cswPct": 0.29}

    mock_compute.side_effect = fake
    series = statcast_season.get_pitcher_statcast_series(401, "cswPct", 2019, 2021)
    assert series["years"] == [2019, 2021]
    assert series["values"] == [0.29, 0.29]
