from utils.formatters import format_stat


def test_avg_drops_leading_zero():
    assert format_stat(0.287, "avg") == ".287"


def test_avg_over_one_keeps_leading_digit():
    assert format_stat(1.0, "avg") == "1.000"


def test_era_two_decimals():
    assert format_stat(3.5, "era") == "3.50"


def test_none_renders_em_dash():
    assert format_stat(None, "avg") == "—"


def test_unmapped_key_passthrough():
    assert format_stat(12, "homeRuns") == "12"
