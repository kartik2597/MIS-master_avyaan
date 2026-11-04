"""Multi-sheet workbooks: every sheet is detected, validated and importable."""

import io

import pytest

pd = pytest.importorskip("pandas")
pytest.importorskip("openpyxl")

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.agent_daily_performance import AgentDailyPerformance
from app.models.agent_shift_adherence import AgentShiftAdherence
from app.models.agent_shrinkage import AgentShrinkage
from app.models.employee import Employee
from app.reports.detector import detect_report_type

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

ROSTER = [
    {"Employee_ID": "EMP001", "Employee_Name": "Test One", "Team": "Support",
     "Designation": "Agent", "Date_Of_Joining": "2025-11-04", "Employment_Status": "Active"},
    {"Employee_ID": "EMP002", "Employee_Name": "Test Two", "Team": "Sales",
     "Designation": "Team Lead", "Date_Of_Joining": "2025-05-08", "Employment_Status": "Active"},
]
DAILY = [
    {"Work_Date": "2026-10-01", "Employee_ID": "EMP001", "Employee_Name": "Test One",
     "Team": "Support", "Shift_Start": "09:00", "Shift_End": "18:00",
     "Attendance_Status": "Present", "Login_Time": "09:08", "Logout_Time": "17:55",
     "Login_Hours": 8.78, "Staff_Time_Hours": 8.78, "Talk_Time_Hours": 3.54,
     "Downtime_Hours": 0.15, "Idle_Time_Hours": 0.73, "Break_Time_Hours": 0.86,
     "Shift_Adherence": "Non Adherent"},
    {"Work_Date": "2026-10-01", "Employee_ID": "EMP002", "Employee_Name": "Test Two",
     "Team": "Sales", "Shift_Start": "07:00", "Shift_End": "16:00",
     "Attendance_Status": "Leave", "Login_Time": None, "Logout_Time": None,
     "Login_Hours": 0, "Staff_Time_Hours": 0, "Talk_Time_Hours": 0,
     "Downtime_Hours": 0, "Idle_Time_Hours": 0, "Break_Time_Hours": 0,
     "Shift_Adherence": "Non Adherent"},
]
SHRINKAGE = [
    {"Work_Date": "2026-10-01", "Employee_ID": "EMP001", "Employee_Name": "Test One",
     "Planned_Shrinkage_Hours": 0, "Unplanned_Shrinkage_Hours": 1},
    {"Work_Date": "2026-10-01", "Employee_ID": "EMP002", "Employee_Name": "Test Two",
     "Planned_Shrinkage_Hours": 9, "Unplanned_Shrinkage_Hours": 0},
]
NOTES = [{"Metric": "Head Count", "Suggested_Test_Definition": "Distinct employees."}]


def workbook(sheets: dict) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for name, rows in sheets.items():
            pd.DataFrame(rows).to_excel(writer, sheet_name=name, index=False)
    return buffer.getvalue()


FULL_WORKBOOK = {
    "Employee_Master": ROSTER,
    "Daily_Activity": DAILY,
    "Shrinkage_Data": SHRINKAGE,
    "Metric_Guide": NOTES,
}


def upload(client, headers, data: bytes, name: str = "MIS_test.xlsx"):
    return client.post(
        "/uploads/file", files={"file": (name, io.BytesIO(data), XLSX)}, headers=headers
    )


def import_report(client, headers, report_type: str, upload_id: str):
    response = client.post(f"/imports/{report_type}/{upload_id}", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def by_type(body: dict) -> dict:
    return {sheet["detected_report_type"]: sheet for sheet in body["sheets"]}


# --- Detection -------------------------------------------------------------


@pytest.mark.parametrize(
    ("columns", "expected"),
    [
        (list(ROSTER[0]), "EMPLOYEE_ROSTER"),
        (list(DAILY[0]), "DAILY_ACTIVITY"),
        (list(SHRINKAGE[0]), "SHRINKAGE_HOURS"),
        (["Metric", "Suggested_Test_Definition"], None),
    ],
)
def test_test_data_sheets_are_detected(columns, expected):
    detection = detect_report_type(columns)

    assert detection.detected_report_type == expected
    if expected:
        assert detection.confidence_score == 100
        assert detection.missing_columns == []


# --- Upload ----------------------------------------------------------------


def test_every_sheet_of_a_workbook_is_detected(client, auth_headers):
    response = upload(client, auth_headers(), workbook(FULL_WORKBOOK))

    assert response.status_code == 201
    body = response.json()
    sheets = by_type(body)
    assert set(sheets) == {"EMPLOYEE_ROSTER", "DAILY_ACTIVITY", "SHRINKAGE_HOURS"}
    assert all(sheet["missing_columns"] == [] for sheet in body["sheets"])
    assert sheets["DAILY_ACTIVITY"]["sheet_name"] == "Daily_Activity"
    assert sheets["DAILY_ACTIVITY"]["total_records"] == 2
    assert body["ignored_sheets"] == ["Metric_Guide"]
    # Each report is its own upload record, all VALIDATED.
    listing = client.get("/uploads", headers=auth_headers()).json()
    assert listing["total"] == 3
    assert {row["upload_status"] for row in listing["items"]} == {"VALIDATED"}


def test_workbook_with_no_known_sheet_reports_unknown(client, auth_headers):
    response = upload(client, auth_headers(), workbook({"Notes": NOTES}))

    assert response.status_code == 201
    body = response.json()
    assert body["detected_report_type"] is None
    assert len(body["sheets"]) == 1


def test_csv_still_returns_a_single_report(client, auth_headers):
    csv_text = pd.DataFrame(ROSTER).to_csv(index=False)
    response = client.post(
        "/uploads/file",
        files={"file": ("roster.csv", io.BytesIO(csv_text.encode()), "text/csv")},
        headers=auth_headers(),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["detected_report_type"] == "EMPLOYEE_ROSTER"
    assert len(body["sheets"]) == 1 and body["sheets"][0]["sheet_name"] is None


# --- Import ----------------------------------------------------------------


def test_all_three_reports_import_into_the_dashboard_tables(client, auth_headers, engine):
    headers = auth_headers()
    sheets = by_type(upload(client, headers, workbook(FULL_WORKBOOK)).json())

    for report_type in ("EMPLOYEE_ROSTER", "DAILY_ACTIVITY", "SHRINKAGE_HOURS"):
        summary = import_report(client, headers, report_type, sheets[report_type]["upload_id"])
        assert summary["total_records"] == 2
        assert summary["processed_records"] == 2
        assert summary["failed_records"] == 0

    with Session(engine) as session:
        assert session.query(Employee).count() == 2
        assert session.query(AgentDailyPerformance).count() == 2
        # Shift adherence exists only for the agent who was present.
        adherence = session.query(AgentShiftAdherence).one()
        assert adherence.emp_id == "EMP001"
        assert adherence.late_login_minutes == 8 and adherence.early_logout_minutes == 5
        assert adherence.non_adherence_flag is True
        assert adherence.login_hours_seconds == 31608  # 8.78 h stored as seconds

        shrinkage = {row.emp_id: row for row in session.query(AgentShrinkage).all()}
        assert float(shrinkage["EMP001"].unplanned_shrinkage) == pytest.approx(11.11)
        assert float(shrinkage["EMP002"].planned_shrinkage) == pytest.approx(100.0)
        assert shrinkage["EMP001"].present_count == 1 and shrinkage["EMP002"].present_count == 0

    kpis = client.get("/dashboard/kpis", headers=headers).json()
    assert kpis["missing_reports"] == []  # DAILY_ACTIVITY fills the APR / daily-performance table
    assert kpis["head_count"] == 2 and kpis["present_count"] == 1


def test_shrinkage_imported_first_picks_up_attendance_later(client, auth_headers, engine):
    headers = auth_headers()
    sheets = by_type(upload(client, headers, workbook(FULL_WORKBOOK)).json())

    import_report(client, headers, "SHRINKAGE_HOURS", sheets["SHRINKAGE_HOURS"]["upload_id"])
    import_report(client, headers, "DAILY_ACTIVITY", sheets["DAILY_ACTIVITY"]["upload_id"])

    with Session(engine) as session:
        record = session.query(AgentShrinkage).filter_by(emp_id="EMP001").one()
        assert record.attendance == "Present" and record.present_count == 1


def test_roster_import_keeps_contact_details_from_master_database(client, auth_headers, engine):
    from datetime import date

    headers = auth_headers()
    with Session(engine) as session:
        session.add(Employee(
            emp_id="EMP001", employee_name="Old Name", email="a@example.com", mobile="999",
            department="Ops", process="Ops", designation="Agent", manager_name="Ravi",
            tl_name="Meera", date_of_joining=date(2025, 1, 1), employment_status="Active",
            location="Pune",
        ))
        session.commit()

    sheets = by_type(upload(client, headers, workbook({"Employee_Master": ROSTER})).json())
    import_report(client, headers, "EMPLOYEE_ROSTER", sheets["EMPLOYEE_ROSTER"]["upload_id"])

    with Session(engine) as session:
        employee = session.query(Employee).filter_by(emp_id="EMP001").one()
        assert employee.employee_name == "Test One"  # roster fields updated
        assert employee.email == "a@example.com" and employee.manager_name == "Ravi"  # kept


def test_bad_rows_are_reported_not_fatal(client, auth_headers):
    headers = auth_headers()
    daily = DAILY + [dict(DAILY[0], Employee_ID="EMP003", Work_Date="not a date")]
    sheets = by_type(upload(client, headers, workbook({"Daily_Activity": daily})).json())

    summary = import_report(client, headers, "DAILY_ACTIVITY", sheets["DAILY_ACTIVITY"]["upload_id"])

    assert summary["total_records"] == 3
    assert summary["processed_records"] == 2 and summary["failed_records"] == 1
    assert "Invalid date value" in summary["message"]


# --- Delete ----------------------------------------------------------------


def test_deleting_one_sheet_keeps_the_shared_file_for_the_others(client, auth_headers):
    headers = auth_headers()
    body = upload(client, headers, workbook(FULL_WORKBOOK)).json()
    sheets = by_type(body)

    deleted = client.delete(f"/uploads/{sheets['EMPLOYEE_ROSTER']['upload_id']}", headers=headers)

    assert deleted.status_code == 204
    stored_files = list((settings.STORAGE_PATH / "uploads").rglob("*.xlsx"))
    assert len(stored_files) == 1  # the other two sheets still point at it

    for report_type in ("DAILY_ACTIVITY", "SHRINKAGE_HOURS"):
        client.delete(f"/uploads/{sheets[report_type]['upload_id']}", headers=headers)
    assert list((settings.STORAGE_PATH / "uploads").rglob("*.xlsx")) == []
