import pytest

# Importing the parser pulls in SQLAlchemy and the models; skip if unavailable.
apr_parser = pytest.importorskip("app.parsers.apr_parser")


def base_row(**overrides):
    row = {
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
    row.update(overrides)
    return row


def test_times_are_stored_in_seconds():
    mapped = apr_parser.map_apr_row(base_row())

    assert mapped["staff_time"] == 8 * 3600
    assert mapped["talk_time"] == 3 * 3600 + 30 * 60
    assert mapped["break_time"] == 45 * 60


def test_excel_duration_strings_are_accepted():
    mapped = apr_parser.map_apr_row(base_row(**{"Staff time": "P0DT8H0M0S"}))

    assert mapped["staff_time"] == 8 * 3600


def test_login_hours_is_not_a_copy_of_staff_time():
    # APR has no login column; login time comes from the shift adherence report.
    mapped = apr_parser.map_apr_row(base_row())

    assert mapped["staff_time"] == 8 * 3600
    assert mapped["login_hours"] == 0


def test_dialflow_calls_are_not_a_copy_of_dialer_calls():
    # Only one call-count column: there is no separate dialflow figure.
    single = apr_parser.map_apr_row(base_row(**{"Total Calls": 50}))
    assert single["dialer_total_calls"] == 50
    assert single["dialflow_total_calls"] == 0

    # Both columns present (differing only in case): each keeps its own value.
    both = apr_parser.map_apr_row(base_row(**{"Total Calls": 50, "Total calls": 48}))
    assert both["dialer_total_calls"] == 50
    assert both["dialflow_total_calls"] == 48
