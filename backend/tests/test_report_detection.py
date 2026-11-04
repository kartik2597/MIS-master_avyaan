import pytest

from app.reports.detector import detect_report_type
from app.reports.validators import validate_uploaded_report


APR_COLUMNS = [
    "Agent ID", "Agent Name", "Date Time", "Campaigns", "User Group", "Attendance",
    "Staff time", "Total Talk Time", "Total Break Time", "Total Idle Time",
    "Productivity %", "Total Calls", "Connected", "Not Connected", "Positive", "TL Remark",
]

SHIFT_ADHERENCE_COLUMNS = [
    "Emp ID", "Emp Name", "Date", "Status", "Process", "Designation", "Manager",
    "Attendance", "Shift in", "Shift out", "Log In", "log out", "Login hours",
    "Downtime", "Login + downtime", "Shift adherence Log IN", "Adhere", "Late login",
    "early logout", "Adherence", "Non Adherence", "Non Adherence %",
]

SHRINKAGE_COLUMNS = [
    "Date", "Emp ID", "Emp Name", "Status", "Process", "Designation", "Manager", "DOS",
    "Login hours", "Attendance", "Age", "Bucket", "Agent count", "P", "A", "LWP", "CL",
    "HD", "TP", "Planned Shrinkage", "Unplanned Shrinkage", "Opening", "Closing",
    "Attrition",
]

MASTER_DATABASE_COLUMNS = [
    "Employee ID", "Employee Name", "Email", "Mobile", "Department", "Process",
    "Designation", "Manager Name", "TL Name", "Date Of Joining", "Employment Status",
    "Location",
]


@pytest.mark.parametrize(
    ("columns", "expected_type"),
    [
        (APR_COLUMNS, "APR"),
        (SHIFT_ADHERENCE_COLUMNS, "SHIFT_ADHERENCE"),
        (SHRINKAGE_COLUMNS, "SHRINKAGE"),
        (MASTER_DATABASE_COLUMNS, "MASTER_DATABASE"),
    ],
)
def test_real_report_headers_are_detected_and_valid(columns, expected_type):
    detection = detect_report_type(columns)

    assert detection.detected_report_type == expected_type
    assert detection.confidence_score == 100

    validation = validate_uploaded_report(expected_type, columns)
    assert validation.valid
    assert validation.missing_columns == []
    assert validation.extra_columns == []


def test_shift_adherence_is_not_confused_with_shrinkage():
    # Both reports share Emp ID, Emp Name, Date, Status, Process and more.
    assert detect_report_type(SHIFT_ADHERENCE_COLUMNS).detected_report_type == "SHIFT_ADHERENCE"
    assert detect_report_type(SHRINKAGE_COLUMNS).detected_report_type == "SHRINKAGE"


def test_unrelated_columns_are_not_detected():
    detection = detect_report_type(["foo", "bar"])

    assert detection.detected_report_type is None
    assert detection.confidence_score == 0
