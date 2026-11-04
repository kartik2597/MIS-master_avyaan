"""Row mapping, row-error reporting and retry rules for the importers."""

from datetime import date, time
from decimal import Decimal
from types import SimpleNamespace

import pytest

pd = pytest.importorskip("pandas")

from app.imports import master_database
from app.parsers import apr_parser, shift_adherence_parser, shrinkage_parser
from app.parsers.upload_status import summarize_row_errors
from app.parsers.utils import parse_percent
from app.services.file_upload import is_importable

MASTER_ROW = {
    "Employee ID": "E100",
    "Employee Name": "Asha Rao",
    "Email": "asha@example.com",
    "Mobile": "9876543210",
    "Department": "Operations",
    "Process": "Sales",
    "Designation": "Agent",
    "Manager Name": "Ravi",
    "TL Name": "Meera",
    "Date Of Joining": "2025-04-01",
    "Employment Status": "Active",
    "Location": "Pune",
}


def master_map(rows):
    return master_database.map_dataframe_to_employees(pd.DataFrame(rows))


# --- Percent handling ------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("87.5%", Decimal("87.5")),  # text with a % sign is taken as written
        (0.875, Decimal("87.5")),  # a real Excel percent cell arrives as a fraction
        (87.5, Decimal("87.5")),  # already in percent points
        (1, Decimal("100")),
        (0, Decimal("0")),
        (None, Decimal("0")),
        ("", Decimal("0")),
    ],
)
def test_parse_percent(value, expected):
    assert parse_percent(value) == expected


def test_percent_cells_reach_the_shrinkage_row_as_percent_points():
    row = {
        "Date": "2026-11-02",
        "Emp ID": "E1",
        "Emp Name": "Asha",
        "Status": "Active",
        "Process": "Sales",
        "Designation": "Agent",
        "Manager": "Ravi",
        "DOS": "2025-01-01",
        "Login hours": "08:00:00",
        "Attendance": "P",
        "Age": 300,
        "Bucket": "180+",
        "Planned Shrinkage": 0.125,
        "Unplanned Shrinkage": "7.5%",
    }

    mapped = shrinkage_parser.map_shrinkage_row(row)

    assert mapped["planned_shrinkage"] == Decimal("12.5")
    assert mapped["unplanned_shrinkage"] == Decimal("7.5")


# --- Master database mapping ----------------------------------------------


def test_master_database_row_maps_all_fields():
    employees, errors = master_map([MASTER_ROW])

    assert errors == []
    assert employees[0]["emp_id"] == "E100"
    assert employees[0]["mobile"] == "9876543210"
    assert employees[0]["date_of_joining"] == date(2025, 4, 1)


def test_master_database_numeric_excel_cells_become_plain_text():
    # Excel stores Mobile and Employee ID as numbers; pandas returns numpy
    # types, which the database driver cannot write into text columns.
    numeric = dict(MASTER_ROW, **{"Employee ID": 100, "Mobile": 9876543210})
    dataframe = pd.DataFrame([numeric])
    assert dataframe["Mobile"].dtype.kind == "i"  # really a numpy integer column

    employees, errors = master_database.map_dataframe_to_employees(dataframe)

    assert errors == []
    assert employees[0]["emp_id"] == "100"
    assert employees[0]["mobile"] == "9876543210"
    assert type(employees[0]["mobile"]) is str


def test_master_database_float_mobile_loses_trailing_zero():
    # A column with a blank cell is read as floats, so 9876543210 -> 9876543210.0.
    rows = [
        dict(MASTER_ROW, **{"Mobile": 9876543210}),
        dict(MASTER_ROW, **{"Employee ID": "E101", "Mobile": None}),
    ]

    employees, errors = master_map(rows)

    assert employees[0]["mobile"] == "9876543210"
    assert [row_number for row_number, _ in errors] == [3]


def test_master_database_blank_field_is_reported_with_row_and_reason():
    good = dict(MASTER_ROW)
    bad = dict(MASTER_ROW, **{"Employee ID": "E101", "Mobile": "", "Location": None})

    employees, errors = master_map([good, bad])

    assert len(employees) == 1
    assert len(errors) == 1
    row_number, reason = errors[0]
    assert row_number == 3  # spreadsheet row: header is row 1, bad row is row 3
    assert "mobile" in reason and "location" in reason


def test_master_database_bad_date_is_reported():
    _, errors = master_map([dict(MASTER_ROW, **{"Date Of Joining": "not a date"})])

    assert errors == [(2, "Invalid date_of_joining")]


def test_master_database_missing_columns_are_named():
    columns = [column for column in MASTER_ROW if column not in {"Mobile", "Location"}]

    with pytest.raises(Exception) as error:
        master_database.ensure_required_columns(columns)

    assert "location" in str(error.value)
    assert "mobile" in str(error.value)


def test_master_database_column_aliases_are_accepted():
    renamed = {
        "emp id": "E1",
        "employee name": "Asha",
        "email": "a@example.com",
        "mobile number": "1",
        "department": "Ops",
        "process": "Sales",
        "designation": "Agent",
        "manager name": "Ravi",
        "team lead": "Meera",
        "doj": "2025-01-01",
        "status": "Active",
        "location": "Pune",
    }

    master_database.ensure_required_columns(list(renamed))  # does not raise


# --- Per-row errors from the report parsers --------------------------------


def raw_record(row_number, raw_data):
    return SimpleNamespace(row_number=row_number, raw_data=raw_data)


def test_apr_failed_rows_are_listed_with_row_number_and_reason():
    good = {
        "Agent ID": "E1",
        "Agent Name": "Asha",
        "Date Time": "2026-11-02",
        "Campaigns": "Sales",
        "User Group": "T1",
        "Attendance": "P",
        "Staff time": "08:00:00",
        "Total Talk Time": "03:00:00",
        "Total Break Time": "00:30:00",
        "Total Idle Time": "00:10:00",
    }
    bad = dict(good, **{"Staff time": "oops"})
    missing = {key: value for key, value in good.items() if key != "Agent ID"}

    rows, errors = apr_parser.map_apr_rows(
        [raw_record(2, good), raw_record(3, bad), raw_record(4, missing)]
    )

    assert len(rows) == 1
    assert [row_number for row_number, _ in errors] == [3, 4]
    assert "Invalid time value" in errors[0][1]
    assert "Agent ID" in errors[1][1]


@pytest.mark.parametrize(
    ("connected", "positive", "expected"),
    [
        (50, 10, Decimal("20.00")),
        (3, 1, Decimal("33.33")),
        (0, 0, Decimal("0")),  # no connected calls: nothing to convert
        (0, 5, Decimal("0")),
    ],
)
def test_apr_conversion_percent_is_positive_over_connected(connected, positive, expected):
    row = {
        "Agent ID": "E1",
        "Agent Name": "Asha",
        "Date Time": "2026-11-02",
        "Campaigns": "Sales",
        "User Group": "T1",
        "Attendance": "P",
        "Staff time": "08:00:00",
        "Total Talk Time": "03:00:00",
        "Total Break Time": "00:30:00",
        "Total Idle Time": "00:10:00",
        "Connected": connected,
        "Positive": positive,
    }

    assert apr_parser.map_apr_row(row)["conversion_percent"] == expected


def test_shift_adherence_failed_row_has_reason():
    rows, errors = shift_adherence_parser.map_shift_adherence_rows(
        [raw_record(2, {"Emp ID": "E1"})]
    )

    assert rows == []
    assert errors[0][0] == 2
    assert "Missing required column value" in errors[0][1]


def test_shrinkage_failed_row_has_reason():
    rows, errors = shrinkage_parser.map_shrinkage_rows(
        [raw_record(7, {"Date": "garbage"})]
    )

    assert rows == []
    assert errors[0][0] == 7
    assert "Invalid date value" in errors[0][1]


def test_row_error_summary():
    assert summarize_row_errors([], 0) is None

    errors = [(row, f"reason {row}") for row in range(2, 20)]
    summary = summarize_row_errors(errors, failed_records=18)

    assert summary.startswith("18 row(s) skipped")
    assert "row 2: reason 2" in summary
    assert "and 8 more" in summary  # only the first 10 are listed


# --- Which uploads may be imported (and retried) ---------------------------


def upload(status, validation_result=None):
    return SimpleNamespace(upload_status=status, validation_result=validation_result)


@pytest.mark.parametrize(
    ("record", "expected"),
    [
        (upload("VALIDATED", {"valid": True}), True),
        (upload("FAILED", {"valid": True}), True),  # import failed: retry allowed
        (upload("FAILED", {"valid": False}), False),  # validation failed
        (upload("FAILED", None), False),
        (upload("PENDING"), False),
        (upload("PROCESSING"), False),
        (upload("COMPLETED"), False),  # already imported; no accidental double run
    ],
)
def test_is_importable(record, expected):
    assert is_importable(record) is expected
