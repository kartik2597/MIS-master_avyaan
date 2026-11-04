from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.parsers.utils import (
    duration_to_minutes,
    parse_bool,
    parse_date,
    parse_decimal,
    parse_int,
    time_to_seconds,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("08:30:00", 30600),
        ("00:00:45", 45),
        ("100:00:00", 360000),
        (timedelta(hours=1, minutes=1), 3660),
        (3600, 3600),
        # Excel stores durations as a fraction of a day.
        (0.5, 43200),
        # pandas writes timedeltas as ISO 8601 durations.
        ("P0DT8H30M0S", 30600),
        ("P1DT0H0M0S", 86400),
        ("PT45S", 45),
        ("P0DT0H0M1.5S", 1),
    ],
)
def test_time_to_seconds(value, expected):
    assert time_to_seconds(value) == expected


@pytest.mark.parametrize("value", ["", None, "8:30", "08:75:00", "abc", "P", "PT"])
def test_time_to_seconds_rejects_bad_values(value):
    with pytest.raises(ValueError):
        time_to_seconds(value)


def test_duration_to_minutes():
    assert duration_to_minutes("00:15:00") == 15
    assert duration_to_minutes("P0DT0H15M0S") == 15
    assert duration_to_minutes(None) == 0
    assert duration_to_minutes(7) == 7


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2026-11-02", date(2026, 11, 2)),
        ("2026-11-02 09:00:00", date(2026, 11, 2)),
        # Ambiguous slash dates are read day-first.
        ("02/11/2026", date(2026, 11, 2)),
        ("13/01/2026", date(2026, 1, 13)),
        (45000, date(2023, 3, 15)),
    ],
)
def test_parse_date(value, expected):
    assert parse_date(value) == expected


def test_parse_date_rejects_garbage():
    with pytest.raises(ValueError):
        parse_date("not a date")


def test_parse_bool():
    assert parse_bool("yes") is True
    assert parse_bool("No") is False
    assert parse_bool("") is False
    with pytest.raises(ValueError):
        parse_bool("maybe")


def test_parse_numbers():
    assert parse_decimal("12.5%") == Decimal("12.5")
    assert parse_decimal("1,234") == Decimal("1234")
    assert parse_decimal(None) == Decimal("0")
    assert parse_int("1,200") == 1200
    with pytest.raises(ValueError):
        parse_decimal("abc")
