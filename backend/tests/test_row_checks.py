"""Row-level value checks used by the APR, shift adherence and shrinkage parsers."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.parsers import apr_parser
from app.parsers.row_checks import check_report_row, find_row_problems

TODAY = date(2026, 11, 3)


def good_row(**overrides):
    row = {
        "emp_id": "E100",
        "report_date": date(2026, 11, 2),
        "staff_time": 8 * 3600,
        "talk_time": 3 * 3600,
        "total_calls": 50,
        "productivity_percent": Decimal("87.5"),
        "planned_shrinkage": Decimal("10"),
        "attrition": 0,
    }
    row.update(overrides)
    return row


def test_a_normal_row_has_no_problems():
    assert find_row_problems(good_row(), today=TODAY) == []
    check_report_row(good_row(), today=TODAY)  # does not raise


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"report_date": date(1999, 12, 31)}, "before 2000"),
        ({"report_date": date(2062, 11, 2)}, "in the future"),
        ({"staff_time": -3600}, "Negative staff time"),
        ({"total_calls": -1}, "Negative total calls"),
        ({"attrition": -2}, "Negative attrition"),
        ({"productivity_percent": Decimal("101")}, "above 100"),
        ({"planned_shrinkage": Decimal("-5")}, "is negative"),
    ],
)
def test_each_kind_of_bad_value_is_reported(overrides, expected):
    problems = find_row_problems(good_row(**overrides), today=TODAY)

    assert len(problems) == 1
    assert expected in problems[0]


def test_percent_of_exactly_100_and_0_is_fine():
    row = good_row(productivity_percent=Decimal("100"), planned_shrinkage=Decimal("0"))

    assert find_row_problems(row, today=TODAY) == []


def test_all_problems_in_a_row_are_listed_together():
    row = good_row(staff_time=-1, productivity_percent=Decimal("150"))

    with pytest.raises(ValueError) as error:
        check_report_row(row, today=TODAY)

    message = str(error.value)
    assert "Negative staff time" in message
    assert "above 100" in message
    assert ";" in message


def test_unknown_employee_is_only_checked_when_a_master_list_is_given():
    row = good_row(emp_id="E999")

    assert find_row_problems(row, known_emp_ids=None, today=TODAY) == []
    assert find_row_problems(row, known_emp_ids={"E100"}, today=TODAY) == [
        "Employee ID E999 is not in the employee master"
    ]
    assert find_row_problems(good_row(), known_emp_ids={"E100"}, today=TODAY) == []


def apr_raw(row_number, **overrides):
    raw = {
        "Agent ID": "E100",
        "Agent Name": "Asha Rao",
        "Date Time": "2026-11-02 09:00:00",
        "Campaigns": "Sales",
        "User Group": "Tier1",
        "Attendance": "P",
        "Staff time": "08:00:00",
        "Total Talk Time": "03:30:00",
        "Total Break Time": "00:45:00",
        "Total Idle Time": "00:20:00",
        "Productivity %": "87.5%",
        "Connected": 40,
        "Not Connected": 10,
        "Positive": 5,
    }
    raw.update(overrides)
    return SimpleNamespace(row_number=row_number, raw_data=raw)


def test_apr_rows_with_bad_values_are_skipped_with_the_row_number():
    records = [
        apr_raw(2),
        apr_raw(3, **{"Date Time": "not a date"}),
        apr_raw(4, **{"Staff time": "-8:00:00"}),
        apr_raw(5, **{"Productivity %": "140%"}),
        apr_raw(6, **{"Agent ID": "E999"}),
    ]

    rows, errors = apr_parser.map_apr_rows(records, known_emp_ids={"E100"})

    assert len(rows) == 1
    assert [row_number for row_number, _ in errors] == [3, 4, 5, 6]
    reasons = dict(errors)
    assert "Invalid date value" in reasons[3]
    assert "Negative staff time" in reasons[4]
    assert "above 100" in reasons[5]
    assert "not in the employee master" in reasons[6]


def test_apr_unknown_employee_check_is_off_by_default():
    rows, errors = apr_parser.map_apr_rows([apr_raw(2, **{"Agent ID": "E999"})])

    assert len(rows) == 1
    assert errors == []
