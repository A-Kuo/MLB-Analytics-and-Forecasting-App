from unittest.mock import MagicMock, patch

from macroservice import roster_history


def _people_response(people: list[dict]):
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"people": people}
    return resp


def _roster_response(entries: list[dict]):
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"roster": entries}
    return resp


def _roster_entry(person_id, name, position="OF"):
    return {"person": {"id": person_id, "fullName": name}, "position": {"abbreviation": position}}


# ---------------------------------------------------------------------------
# get_alltime_roster
# ---------------------------------------------------------------------------


@patch("macroservice.roster_history.request_with_backoff")
def test_alltime_roster_parses_entries(mock_request):
    mock_request.return_value = _roster_response(
        [_roster_entry(1, "Player One", "SS"), _roster_entry(2, "Player Two", "P")]
    )
    roster = roster_history.get_alltime_roster(1001)
    assert roster == [
        {"id": 1, "name": "Player One", "positions": ["SS"], "is_pitcher": False},
        {"id": 2, "name": "Player Two", "positions": ["P"], "is_pitcher": True},
    ]


@patch("macroservice.roster_history.request_with_backoff")
def test_alltime_roster_requests_rostertype_alltime(mock_request):
    mock_request.return_value = _roster_response([])
    roster_history.get_alltime_roster(1002)
    _, kwargs = mock_request.call_args
    assert kwargs["params"] == {"rosterType": "allTime"}


@patch("macroservice.roster_history.request_with_backoff")
def test_alltime_roster_normalizes_generic_of_to_outfield_positions(mock_request):
    mock_request.return_value = _roster_response([_roster_entry(1, "Generic Player", "OF")])
    roster = roster_history.get_alltime_roster(9999)  # Use a different team_id to bypass cache
    assert roster == [
        {"id": 1, "name": "Generic Player", "positions": ["LF", "CF", "RF"], "is_pitcher": False},
    ]


# ---------------------------------------------------------------------------
# _get_people_batch chunking
# ---------------------------------------------------------------------------


@patch("macroservice.roster_history.request_with_backoff")
def test_people_batch_chunks_large_id_lists(mock_request):
    ids = tuple(range(1200))  # > 2x PEOPLE_BATCH_CHUNK_SIZE (500)
    mock_request.side_effect = lambda *a, **kw: _people_response(
        [{"id": int(pid), "mlbDebutDate": "2020-01-01", "active": True} for pid in kw["params"]["personIds"].split(",")]
    )
    result = roster_history._get_people_batch(ids)
    assert mock_request.call_count == 3  # 500 + 500 + 200
    assert len(result) == 1200
    assert result[0]["debut_year"] == 2020


@patch("macroservice.roster_history.request_with_backoff")
def test_people_batch_debut_year_and_active_flag(mock_request):
    mock_request.return_value = _people_response(
        [{"id": 121578, "mlbDebutDate": "1914-07-11", "lastPlayedDate": "1935-05-30", "active": False}]
    )
    result = roster_history._get_people_batch((121578,))
    assert result[121578] == {"debut_year": 1914, "last_active_year": 1935, "active": False}


@patch("macroservice.roster_history.request_with_backoff")
def test_people_batch_still_active_has_no_last_active_year(mock_request):
    # lastPlayedDate is absent (not null) for a currently active player.
    mock_request.return_value = _people_response([{"id": 682998, "mlbDebutDate": "2022-08-29", "active": True}])
    result = roster_history._get_people_batch((682998,))
    assert result[682998] == {"debut_year": 2022, "last_active_year": None, "active": True}


# ---------------------------------------------------------------------------
# _active_year_ranges / _active_years_label
# ---------------------------------------------------------------------------


def test_active_year_ranges_still_active():
    assert roster_history._active_year_ranges({"debut_year": 2022, "last_active_year": None}) == [(2022, None)]


def test_active_year_ranges_retired():
    assert roster_history._active_year_ranges({"debut_year": 1998, "last_active_year": 2004}) == [(1998, 2004)]


def test_active_year_ranges_missing_debut():
    assert roster_history._active_year_ranges({"debut_year": None, "last_active_year": None}) == []


def test_active_years_label_still_active():
    assert roster_history._active_years_label([(2022, None)]) == "2022–present"


def test_active_years_label_retired():
    assert roster_history._active_years_label([(1998, 2004)]) == "1998–2004"


def test_active_years_label_no_ranges():
    assert roster_history._active_years_label([]) == ""


def test_active_years_label_multiple_ranges():
    assert roster_history._active_years_label([(1990, 1994), (1998, None)]) == "1990–1994, 1998–present"


# ---------------------------------------------------------------------------
# get_team_roster_with_active_years
# ---------------------------------------------------------------------------


@patch("macroservice.roster_history._get_people_batch")
@patch("macroservice.roster_history.get_alltime_roster")
def test_roster_with_active_years_merges_bio_data(mock_alltime, mock_batch):
    mock_alltime.return_value = [{"id": 1, "name": "Player One", "positions": ["OF"], "is_pitcher": False}]
    mock_batch.return_value = {1: {"debut_year": 2015, "last_active_year": None, "active": True}}
    enriched = roster_history.get_team_roster_with_active_years(1001)
    assert enriched == [
        {
            "id": 1,
            "name": "Player One",
            "positions": ["OF"],
            "is_pitcher": False,
            "debut_year": 2015,
            "last_active_year": None,
            "active": True,
            "active_year_ranges": [(2015, None)],
            "active_years_label": "2015–present",
        }
    ]


@patch("macroservice.roster_history._get_people_batch")
@patch("macroservice.roster_history.get_alltime_roster")
def test_roster_with_active_years_handles_missing_bio(mock_alltime, mock_batch):
    mock_alltime.return_value = [{"id": 1, "name": "Ghost Player", "positions": ["OF"], "is_pitcher": False}]
    mock_batch.return_value = {}  # bio lookup returned nothing for this id
    enriched = roster_history.get_team_roster_with_active_years(1001)
    assert enriched[0]["debut_year"] is None
    assert enriched[0]["active_year_ranges"] == []
    assert enriched[0]["active_years_label"] == ""


# ---------------------------------------------------------------------------
# resolve_players_in_range
# ---------------------------------------------------------------------------


def _entry(id_, positions, debut_year, last_active_year):
    return {
        "id": id_,
        "name": f"Player {id_}",
        "positions": positions,
        "is_pitcher": "P" in positions,
        "debut_year": debut_year,
        "last_active_year": last_active_year,
        "active": last_active_year is None,
        "active_year_ranges": [(debut_year, last_active_year)] if debut_year is not None else [],
        "active_years_label": "",
    }


@patch("macroservice.roster_history.get_team_roster_with_active_years")
def test_resolve_excludes_player_entirely_before_range(mock_roster):
    mock_roster.return_value = [_entry(1, ["OF"], 1990, 1995)]
    assert roster_history.resolve_players_in_range(1001, 2000, 2010) == set()


@patch("macroservice.roster_history.get_team_roster_with_active_years")
def test_resolve_excludes_player_entirely_after_range(mock_roster):
    mock_roster.return_value = [_entry(1, ["OF"], 2015, 2020)]
    assert roster_history.resolve_players_in_range(1001, 2000, 2010) == set()


@patch("macroservice.roster_history.get_team_roster_with_active_years")
def test_resolve_includes_player_spanning_range(mock_roster):
    mock_roster.return_value = [_entry(1, ["OF"], 1995, 2005)]
    assert roster_history.resolve_players_in_range(1001, 2000, 2010) == {1}


@patch("macroservice.roster_history.get_team_roster_with_active_years")
def test_resolve_includes_still_active_player_debuted_before_range_ends(mock_roster):
    mock_roster.return_value = [_entry(1, ["OF"], 2018, None)]
    assert roster_history.resolve_players_in_range(1001, 2015, 2020) == {1}


@patch("macroservice.roster_history.get_team_roster_with_active_years")
def test_resolve_excludes_player_who_debuts_after_range_even_if_still_active(mock_roster):
    mock_roster.return_value = [_entry(1, ["OF"], 2025, None)]
    assert roster_history.resolve_players_in_range(1001, 2015, 2020) == set()


@patch("macroservice.roster_history.get_team_roster_with_active_years")
def test_resolve_excludes_players_with_no_known_debut_year(mock_roster):
    mock_roster.return_value = [_entry(1, ["OF"], None, None)]
    assert roster_history.resolve_players_in_range(1001, 2000, 2010) == set()


@patch("macroservice.roster_history.get_team_roster_with_active_years")
def test_resolve_filters_by_single_position(mock_roster):
    mock_roster.return_value = [_entry(1, ["OF"], 2000, 2010), _entry(2, ["P"], 2000, 2010)]
    assert roster_history.resolve_players_in_range(1001, 2000, 2010, positions=frozenset({"OF"})) == {1}


@patch("macroservice.roster_history.get_team_roster_with_active_years")
def test_resolve_filters_by_position_group_set(mock_roster):
    mock_roster.return_value = [
        _entry(1, ["1B"], 2000, 2010),
        _entry(2, ["SS"], 2000, 2010),
        _entry(3, ["P"], 2000, 2010),
    ]
    infield = frozenset({"1B", "2B", "3B", "SS"})
    assert roster_history.resolve_players_in_range(1001, 2000, 2010, positions=infield) == {1, 2}


@patch("macroservice.roster_history.get_team_roster_with_active_years")
def test_resolve_matches_multi_position_player_on_any_listed_position(mock_roster):
    mock_roster.return_value = [_entry(1, ["2B", "OF"], 2000, 2010)]
    assert roster_history.resolve_players_in_range(1001, 2000, 2010, positions=frozenset({"OF"})) == {1}


@patch("macroservice.roster_history.get_team_roster_with_active_years")
def test_resolve_no_position_filter_returns_everyone_in_range(mock_roster):
    mock_roster.return_value = [_entry(1, ["OF"], 2000, 2010), _entry(2, ["P"], 2000, 2010)]
    assert roster_history.resolve_players_in_range(1001, 2000, 2010) == {1, 2}


@patch("macroservice.roster_history.get_team_roster_with_active_years")
def test_resolve_same_year_range_matches_players_active_that_year(mock_roster):
    mock_roster.return_value = [_entry(1, ["OF"], 2000, 2010)]
    assert roster_history.resolve_players_in_range(1001, 2005, 2005) == {1}
