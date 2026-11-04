"""Project & Timesheet and Hiring & Attrition: detection, import and dashboards."""

import io
from datetime import date

import pytest

pd = pytest.importorskip("pandas")
pytest.importorskip("openpyxl")

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.employee import Employee
from app.models.employee_movement import EmployeeMovement
from app.models.project_timesheet import ProjectTimesheet
from app.models.user import UserRole
from app.reports.detector import detect_report_type

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

TIMESHEET = [
    {"Work_Date": "2026-10-01", "Employee_ID": "A1", "Employee_Name": "Agent One",
     "Project_Name": "Alpha", "Client_Name": "Acme", "Task_Type": "Dev",
     "Billable": "Yes", "Hours_Logged": 6},
    {"Work_Date": "2026-10-01", "Employee_ID": "A1", "Employee_Name": "Agent One",
     "Project_Name": "Alpha", "Client_Name": "Acme", "Task_Type": "Meeting",
     "Billable": "No", "Hours_Logged": 2},
    {"Work_Date": "2026-10-01", "Employee_ID": "A2", "Employee_Name": "Agent Two",
     "Project_Name": "Beta", "Client_Name": "Globex", "Task_Type": "Dev",
     "Billable": "Yes", "Hours_Logged": 8},
    {"Work_Date": "2026-10-02", "Employee_ID": "A3", "Employee_Name": "Agent Three",
     "Project_Name": "Alpha", "Client_Name": "Acme", "Task_Type": "Dev",
     "Billable": "Yes", "Hours_Logged": 4},
]
# 20 hours in total, 18 of them billable (90%), 3 people, 2 projects.

MOVEMENTS = [
    {"Employee_ID": "N1", "Employee_Name": "New One", "Event_Type": "New Hire",
     "Event_Date": "2026-10-05", "Team": "Support", "Designation": "Agent",
     "Manager_Name": "Meera Shah", "Exit_Reason": None, "Hiring_Source": "Referral"},
    {"Employee_ID": "N2", "Employee_Name": "New Two", "Event_Type": "Joined",
     "Event_Date": "2026-10-10", "Team": "Sales", "Designation": "Agent",
     "Manager_Name": "Other Manager", "Exit_Reason": None, "Hiring_Source": "Campus"},
    {"Employee_ID": "A1", "Employee_Name": "Agent One", "Event_Type": "Resigned",
     "Event_Date": "2026-10-15", "Team": "Support", "Designation": "Agent",
     "Manager_Name": "Meera Shah", "Exit_Reason": "Better offer", "Hiring_Source": None},
    {"Employee_ID": "A3", "Employee_Name": "Agent Three", "Event_Type": "Left",
     "Event_Date": "2026-10-20", "Team": "Sales", "Designation": "Agent",
     "Manager_Name": "Other Manager", "Exit_Reason": None, "Hiring_Source": None},
    # No team in the file: it is taken from the employee master (Support).
    {"Employee_ID": "A5", "Employee_Name": "Agent Five", "Event_Type": "Terminated",
     "Event_Date": "2026-10-25", "Team": None, "Designation": None,
     "Manager_Name": None, "Exit_Reason": None, "Hiring_Source": None},
]


@pytest.fixture(autouse=True)
def manual_import(monkeypatch):
    """Keep uploads PENDING until the test imports them, as in the other upload tests."""
    monkeypatch.setattr(settings, "AUTO_PROCESS_UPLOADS", False)


def workbook(sheets: dict) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for name, rows in sheets.items():
            pd.DataFrame(rows).to_excel(writer, sheet_name=name, index=False)
    return buffer.getvalue()


def upload(client, headers, data: bytes, name: str = "MIS_test.xlsx"):
    return client.post(
        "/uploads/file", files={"file": (name, io.BytesIO(data), XLSX)}, headers=headers
    )


def upload_and_import(client, headers, report_type: str, sheet: str, rows: list[dict]) -> dict:
    response = upload(client, headers, workbook({sheet: rows}))
    assert response.status_code == 201, response.text
    sheets = {item["detected_report_type"]: item for item in response.json()["sheets"]}
    assert report_type in sheets, f"{report_type} not detected, got {list(sheets)}"
    imported = client.post(
        f"/imports/{report_type}/{sheets[report_type]['upload_id']}", headers=headers
    )
    assert imported.status_code == 200, imported.text
    return imported.json()


def employee(emp_id, name, *, manager="", tl="", process="Support", status="Active"):
    return Employee(
        emp_id=emp_id,
        employee_name=name,
        email=f"{emp_id.lower()}@example.com",
        mobile="9999999999",
        department="Ops",
        process=process,
        designation="Agent",
        manager_name=manager,
        tl_name=tl,
        date_of_joining=date(2025, 1, 1),
        employment_status=status,
        location="Indore",
    )


@pytest.fixture()
def master(engine):
    """Manager M1 (Meera Shah) owns A1, A2 and A4. A3 and A5 report to someone else."""
    with Session(engine) as session:
        session.add_all(
            [
                employee("M1", "Meera Shah"),
                employee("A1", "Agent One", manager="Meera Shah", tl="Tara Rao"),
                employee("A2", "Agent Two", manager="Meera Shah", tl="Tara Rao"),
                employee("A3", "Agent Three", manager="Other Manager", process="Sales"),
                # Active with no hours logged: this is the bench.
                employee("A4", "Agent Four", manager="Meera Shah", tl="Tara Rao"),
                # Gone from the company: never on the bench.
                employee("A5", "Agent Five", manager="Other Manager", status="Resigned"),
            ]
        )
        session.commit()


def manager_headers(client, make_user):
    make_user(role=UserRole.MANAGER, email="meera@mismaster.com", emp_id="M1")
    response = client.post(
        "/auth/login", json={"email": "meera@mismaster.com", "password": "Password123"}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


# --- Detection -------------------------------------------------------------


@pytest.mark.parametrize(
    ("columns", "expected"),
    [
        (list(TIMESHEET[0]), "PROJECT_TIMESHEET"),
        (list(MOVEMENTS[0]), "HIRING_ATTRITION"),
        # The older report layouts must not be mistaken for the new ones.
        (
            ["Employee_ID", "Employee_Name", "Team", "Designation",
             "Date_Of_Joining", "Employment_Status"],
            "EMPLOYEE_ROSTER",
        ),
        (
            ["Work_Date", "Employee_ID", "Employee_Name", "Attendance_Status"],
            "DAILY_ACTIVITY",
        ),
    ],
)
def test_new_reports_are_detected_without_stealing_old_ones(columns, expected):
    detection = detect_report_type(columns)

    assert detection.detected_report_type == expected
    assert detection.confidence_score == 100


def test_timesheet_aliases_are_understood():
    detection = detect_report_type(
        ["Timesheet Date", "Emp Code", "Emp Name", "Project", "Hours Worked"]
    )

    assert detection.detected_report_type == "PROJECT_TIMESHEET"
    assert detection.missing_columns == []


# --- Project timesheet import ----------------------------------------------


def test_timesheet_import_stores_hours_and_billable_flag(client, auth_headers, engine, master):
    summary = upload_and_import(client, auth_headers(), "PROJECT_TIMESHEET", "Timesheet", TIMESHEET)

    assert (summary["total_records"], summary["processed_records"], summary["failed_records"]) == (4, 4, 0)
    with Session(engine) as session:
        rows = {(r.emp_id, r.task_type): r for r in session.query(ProjectTimesheet).all()}
        assert len(rows) == 4
        assert float(rows[("A1", "Dev")].hours) == 6.0 and rows[("A1", "Dev")].billable is True
        assert rows[("A1", "Meeting")].billable is False
        assert rows[("A1", "Dev")].client_name == "Acme"


def test_timesheet_bad_hours_are_skipped_not_fatal(client, auth_headers, engine, master):
    rows = TIMESHEET + [
        dict(TIMESHEET[0], Employee_ID="A2", Project_Name="Gamma", Hours_Logged=30),
        dict(TIMESHEET[0], Employee_ID="A2", Project_Name="Delta", Hours_Logged=0),
    ]

    summary = upload_and_import(client, auth_headers(), "PROJECT_TIMESHEET", "Timesheet", rows)

    assert summary["total_records"] == 6
    assert summary["processed_records"] == 4 and summary["failed_records"] == 2
    assert "Hours logged" in summary["message"]
    with Session(engine) as session:
        assert session.query(ProjectTimesheet).count() == 4


def test_timesheet_reupload_updates_instead_of_duplicating(client, auth_headers, engine, master):
    headers = auth_headers()
    upload_and_import(client, headers, "PROJECT_TIMESHEET", "Timesheet", TIMESHEET)
    corrected = [dict(TIMESHEET[0], Hours_Logged=7)] + TIMESHEET[1:]  # a different file

    upload_and_import(client, headers, "PROJECT_TIMESHEET", "Timesheet", corrected)

    with Session(engine) as session:
        assert session.query(ProjectTimesheet).count() == 4
        row = session.query(ProjectTimesheet).filter_by(emp_id="A1", task_type="Dev").one()
        assert float(row.hours) == 7.0


def test_timesheet_duplicate_rows_in_one_file_keep_the_last(client, auth_headers, engine, master):
    rows = TIMESHEET + [dict(TIMESHEET[0], Hours_Logged=7)]

    summary = upload_and_import(client, auth_headers(), "PROJECT_TIMESHEET", "Timesheet", rows)

    assert "duplicate" in summary["message"]
    with Session(engine) as session:
        assert session.query(ProjectTimesheet).count() == 4
        row = session.query(ProjectTimesheet).filter_by(emp_id="A1", task_type="Dev").one()
        assert float(row.hours) == 7.0


# --- Project dashboard ------------------------------------------------------


def test_project_summary_totals(client, auth_headers, master):
    headers = auth_headers()
    upload_and_import(client, headers, "PROJECT_TIMESHEET", "Timesheet", TIMESHEET)

    body = client.get("/dashboard/projects/summary", headers=headers).json()

    assert body["has_data"] is True
    assert body["total_hours"] == 20.0
    assert body["billable_hours"] == 18.0 and body["non_billable_hours"] == 2.0
    assert body["billable_percent"] == 90.0
    assert body["employees_logged"] == 3 and body["active_projects"] == 2
    assert body["avg_hours_per_employee"] == pytest.approx(6.67, abs=0.01)


def test_project_summary_without_data_says_so(client, auth_headers):
    body = client.get("/dashboard/projects/summary", headers=auth_headers()).json()

    assert body["has_data"] is False
    assert body["total_hours"] == 0 and body["billable_percent"] is None


def test_hours_per_project_are_ranked_with_share(client, auth_headers, master):
    headers = auth_headers()
    upload_and_import(client, headers, "PROJECT_TIMESHEET", "Timesheet", TIMESHEET)

    items = client.get("/dashboard/projects/projects", headers=headers).json()["items"]

    assert [item["project_name"] for item in items] == ["Alpha", "Beta"]
    alpha, beta = items
    assert alpha["total_hours"] == 12.0 and alpha["employees"] == 2
    assert alpha["client_name"] == "Acme"
    assert alpha["share_percent"] == 60.0 and beta["share_percent"] == 40.0


def test_employee_hours_table_searches_and_pages(client, auth_headers, master):
    headers = auth_headers()
    upload_and_import(client, headers, "PROJECT_TIMESHEET", "Timesheet", TIMESHEET)

    everyone = client.get("/dashboard/projects/employees", headers=headers).json()
    found = client.get(
        "/dashboard/projects/employees", headers=headers, params={"search": "agent one"}
    ).json()

    assert everyone["total"] == 3
    # A1 and A2 both logged 8 hours (a tie goes to the lower Employee ID); A3 logged 4.
    assert [row["emp_id"] for row in everyone["items"]] == ["A1", "A2", "A3"]
    assert [row["emp_id"] for row in found["items"]] == ["A1"]
    assert found["items"][0]["billable_percent"] == 75.0  # 6 of 8 hours
    assert found["items"][0]["days_logged"] == 1


def test_bench_lists_active_people_with_no_hours(client, auth_headers, master):
    headers = auth_headers()
    upload_and_import(client, headers, "PROJECT_TIMESHEET", "Timesheet", TIMESHEET)

    bench = client.get("/dashboard/projects/bench", headers=headers).json()

    # A4 and the manager M1 logged nothing. A5 resigned, so is not "on the bench".
    assert {row["emp_id"] for row in bench["items"]} == {"A4", "M1"}
    assert bench["total"] == 2


def test_bench_is_empty_when_no_timesheet_was_uploaded(client, auth_headers, master):
    bench = client.get("/dashboard/projects/bench", headers=auth_headers()).json()

    assert bench["total"] == 0 and bench["items"] == []


def test_project_trends_give_one_point_per_day(client, auth_headers, master):
    headers = auth_headers()
    upload_and_import(client, headers, "PROJECT_TIMESHEET", "Timesheet", TIMESHEET)

    points = client.get("/dashboard/projects/trends", headers=headers).json()["points"]

    assert [p["report_date"] for p in points] == ["2026-10-01", "2026-10-02"]
    assert [p["total_hours"] for p in points] == [16.0, 4.0]
    assert [p["billable_hours"] for p in points] == [14.0, 4.0]


def test_project_dashboard_is_limited_to_a_managers_team(client, auth_headers, make_user, master):
    admin = auth_headers()
    upload_and_import(client, admin, "PROJECT_TIMESHEET", "Timesheet", TIMESHEET)
    manager = manager_headers(client, make_user)

    mine = client.get("/dashboard/projects/summary", headers=manager).json()
    my_bench = client.get("/dashboard/projects/bench", headers=manager).json()
    my_people = client.get("/dashboard/projects/employees", headers=manager).json()

    assert mine["total_hours"] == 16.0  # A1 + A2, not A3's 4 hours
    assert mine["employees_logged"] == 2
    assert {row["emp_id"] for row in my_people["items"]} == {"A1", "A2"}
    assert [row["emp_id"] for row in my_bench["items"]] == ["A4"]


def test_project_filters_narrow_an_admin_view(client, auth_headers, master):
    headers = auth_headers()
    upload_and_import(client, headers, "PROJECT_TIMESHEET", "Timesheet", TIMESHEET)

    body = client.get(
        "/dashboard/projects/summary", headers=headers, params={"emp_id": "A3"}
    ).json()

    assert body["total_hours"] == 4.0 and body["employees_logged"] == 1


def test_project_date_range_must_be_in_order(client, auth_headers):
    response = client.get(
        "/dashboard/projects/summary",
        headers=auth_headers(),
        params={"date_from": "2026-10-05", "date_to": "2026-10-01"},
    )

    assert response.status_code == 400


def test_project_dashboards_require_login(client):
    for path in ("summary", "projects", "employees", "bench", "trends"):
        assert client.get(f"/dashboard/projects/{path}").status_code == 401


# --- Hiring & attrition import ----------------------------------------------


def test_movement_import_classifies_events_and_reasons(client, auth_headers, engine, master):
    summary = upload_and_import(client, auth_headers(), "HIRING_ATTRITION", "Hiring", MOVEMENTS)

    assert (summary["total_records"], summary["processed_records"], summary["failed_records"]) == (5, 5, 0)
    with Session(engine) as session:
        rows = {r.emp_id: r for r in session.query(EmployeeMovement).all()}
        assert rows["N1"].event_type == "JOINED" and rows["N1"].hiring_source == "Referral"
        assert rows["N1"].reason == ""
        assert rows["A1"].event_type == "LEFT" and rows["A1"].reason == "Better offer"
        # "Terminated" says why they left, so it becomes the reason.
        assert rows["A5"].event_type == "LEFT" and rows["A5"].reason == "Terminated"
        # A plain "Left" with no reason stays blank instead of inventing one.
        assert rows["A3"].reason == ""
        # Team and manager were blank in the file: taken from the employee master.
        assert rows["A5"].team == "Support" and rows["A5"].manager_name == "Other Manager"


def test_movement_unknown_event_type_is_skipped(client, auth_headers, engine, master):
    rows = MOVEMENTS + [dict(MOVEMENTS[0], Employee_ID="N9", Event_Type="Transferred")]

    summary = upload_and_import(client, auth_headers(), "HIRING_ATTRITION", "Hiring", rows)

    assert summary["failed_records"] == 1
    assert "Unknown event type" in summary["message"]
    with Session(engine) as session:
        assert session.query(EmployeeMovement).count() == 5


def test_movement_reupload_updates_instead_of_duplicating(client, auth_headers, engine, master):
    headers = auth_headers()
    upload_and_import(client, headers, "HIRING_ATTRITION", "Hiring", MOVEMENTS)
    changed = [dict(MOVEMENTS[2], Exit_Reason="Relocation")] + MOVEMENTS[:2] + MOVEMENTS[3:]

    upload_and_import(client, headers, "HIRING_ATTRITION", "Hiring", changed)

    with Session(engine) as session:
        assert session.query(EmployeeMovement).count() == 5
        assert session.query(EmployeeMovement).filter_by(emp_id="A1").one().reason == "Relocation"


# --- Hiring dashboard --------------------------------------------------------


def test_hiring_summary_counts_and_attrition_rate(client, auth_headers, master):
    headers = auth_headers()
    upload_and_import(client, headers, "HIRING_ATTRITION", "Hiring", MOVEMENTS)

    body = client.get("/dashboard/hiring/summary", headers=headers).json()

    assert body["has_data"] is True
    assert (body["joiners"], body["leavers"], body["net_change"]) == (2, 3, -1)
    # Six people in the master before the period, two joined, three left.
    assert body["opening_headcount"] == 6 and body["closing_headcount"] == 5
    # 3 leavers over the average headcount of 5.5.
    assert body["attrition_percent"] == pytest.approx(54.55, abs=0.01)
    reasons = {item["reason"]: item["count"] for item in body["top_exit_reasons"]}
    assert reasons == {"Better offer": 1, "Terminated": 1}


def test_hiring_summary_without_data_says_so(client, auth_headers):
    body = client.get("/dashboard/hiring/summary", headers=auth_headers()).json()

    assert body["has_data"] is False
    assert body["attrition_percent"] is None and body["opening_headcount"] is None


def test_hiring_teams_rank_the_team_losing_most_people_first(client, auth_headers, master):
    headers = auth_headers()
    upload_and_import(client, headers, "HIRING_ATTRITION", "Hiring", MOVEMENTS)

    items = client.get("/dashboard/hiring/teams", headers=headers).json()["items"]

    assert [(t["team"], t["joiners"], t["leavers"]) for t in items] == [
        ("Support", 1, 2),
        ("Sales", 1, 1),
    ]


def test_hiring_trends_fill_months_with_no_events(client, auth_headers, master):
    headers = auth_headers()
    upload_and_import(client, headers, "HIRING_ATTRITION", "Hiring", MOVEMENTS)

    points = client.get(
        "/dashboard/hiring/trends",
        headers=headers,
        params={"date_from": "2026-09-01", "date_to": "2026-10-31"},
    ).json()["points"]

    assert [(p["month"], p["joiners"], p["leavers"]) for p in points] == [
        ("2026-09", 0, 0),
        ("2026-10", 2, 3),
    ]


def test_hiring_events_filter_by_type_and_search(client, auth_headers, master):
    headers = auth_headers()
    upload_and_import(client, headers, "HIRING_ATTRITION", "Hiring", MOVEMENTS)

    leavers = client.get(
        "/dashboard/hiring/events", headers=headers, params={"event_type": "LEFT"}
    ).json()
    found = client.get(
        "/dashboard/hiring/events", headers=headers, params={"search": "new two"}
    ).json()

    assert leavers["total"] == 3
    assert [row["emp_id"] for row in leavers["items"]] == ["A5", "A3", "A1"]  # newest first
    assert [row["emp_id"] for row in found["items"]] == ["N2"]
    assert found["items"][0]["detail"] == "Campus"
    assert client.get(
        "/dashboard/hiring/events", headers=headers, params={"event_type": "QUIT"}
    ).status_code == 422


def test_hiring_dashboard_is_limited_to_a_managers_team(client, auth_headers, make_user, master):
    admin = auth_headers()
    upload_and_import(client, admin, "HIRING_ATTRITION", "Hiring", MOVEMENTS)
    manager = manager_headers(client, make_user)

    mine = client.get("/dashboard/hiring/summary", headers=manager).json()
    events = client.get("/dashboard/hiring/events", headers=manager).json()

    # Meera sees her own leaver (A1) and the joiner assigned to her (N1). The joiner
    # was added to Employee Master by the upload. Other teams' people stay hidden.
    assert (mine["joiners"], mine["leavers"]) == (1, 1)
    assert [row["emp_id"] for row in events["items"]] == ["A1", "N1"]  # newest first


def test_hiring_dashboards_require_login(client):
    for path in ("summary", "trends", "teams", "events"):
        assert client.get(f"/dashboard/hiring/{path}").status_code == 401


# --- Unknown people are added to Employee Master -----------------------------


def test_timesheet_adds_unknown_employees_to_the_master(client, auth_headers, engine, master):
    rows = TIMESHEET + [dict(TIMESHEET[0], Employee_ID="Z9", Employee_Name="Zed New")]

    upload_and_import(client, auth_headers(), "PROJECT_TIMESHEET", "Timesheet", rows)

    with Session(engine) as session:
        new = session.query(Employee).filter_by(emp_id="Z9").one()
        assert new.employee_name == "Zed New" and new.employment_status == "Active"
        assert new.date_of_joining == date(2026, 10, 1)  # first day seen
        # People already in the master are not changed.
        assert session.query(Employee).filter_by(emp_id="A1").one().manager_name == "Meera Shah"
        assert session.query(Employee).count() == 7


def test_hiring_adds_unknown_joiners_and_leavers_to_the_master(client, auth_headers, engine, master):
    rows = MOVEMENTS + [dict(MOVEMENTS[3], Employee_ID="X7", Employee_Name="Gone Person")]

    upload_and_import(client, auth_headers(), "HIRING_ATTRITION", "Hiring", rows)

    with Session(engine) as session:
        joiner = session.query(Employee).filter_by(emp_id="N1").one()
        assert joiner.employment_status == "Active"
        assert joiner.date_of_joining == date(2026, 10, 5)  # the joining date in the file
        assert (joiner.process, joiner.designation) == ("Support", "Agent")
        assert joiner.manager_name == "Meera Shah"
        # A leaver nobody knew about is added as Resigned, so never "on the bench".
        leaver = session.query(Employee).filter_by(emp_id="X7").one()
        assert leaver.employment_status == "Resigned" and leaver.process == "Sales"
        # People already in the master keep their status.
        assert session.query(Employee).filter_by(emp_id="A1").one().employment_status == "Active"


def test_new_joiner_is_visible_to_their_manager_straight_away(client, auth_headers, make_user, master):
    upload_and_import(client, auth_headers(), "HIRING_ATTRITION", "Hiring", MOVEMENTS)
    manager = manager_headers(client, make_user)

    options = client.get("/dashboard/filters", headers=manager).json()

    assert "Meera Shah" in options["managers"]
    found = client.get(
        "/dashboard/hiring/events", headers=manager, params={"search": "New One"}
    ).json()
    assert [row["emp_id"] for row in found["items"]] == ["N1"]


# --- NA / N/A is real text, not a blank cell ---------------------------------


def test_na_is_kept_as_text_in_the_master_import(client, auth_headers, engine):
    row = {
        "Employee ID": "T9", "Employee Name": "Top Level", "Email": "t9@example.com",
        "Mobile": "9876543210", "Department": "Ops", "Process": "Support",
        "Designation": "Manager", "Manager Name": "Anil Mehta", "TL Name": "NA",
        "Date Of Joining": "2025-01-01", "Employment Status": "Active", "Location": "Indore",
    }

    summary = upload_and_import(client, auth_headers(), "MASTER_DATABASE", "Master_Database", [row])

    assert (summary["processed_records"], summary["failed_records"]) == (1, 0)
    with Session(engine) as session:
        assert session.query(Employee).filter_by(emp_id="T9").one().tl_name == "NA"


def test_a_truly_empty_cell_is_still_blank_in_the_master_import(client, auth_headers):
    row = {
        "Employee ID": "T8", "Employee Name": "No Lead", "Email": "t8@example.com",
        "Mobile": "9876543210", "Department": "Ops", "Process": "Support",
        "Designation": "Agent", "Manager Name": "Anil Mehta", "TL Name": None,
        "Date Of Joining": "2025-01-01", "Employment Status": "Active", "Location": "Indore",
    }

    summary = upload_and_import(client, auth_headers(), "MASTER_DATABASE", "Master_Database", [row])

    assert summary["failed_records"] == 1
    assert "tl_name" in summary["message"]


def test_na_in_a_number_column_still_counts_as_blank(client, auth_headers):
    row = {
        "Work_Date": "2026-10-01", "Employee_ID": "A1", "Employee_Name": "Agent One",
        "Team": "Support", "Attendance_Status": "Absent", "Login_Hours": "NA",
        "Staff_Time_Hours": "N/A", "Talk_Time_Hours": 0, "Idle_Time_Hours": "null",
        "Break_Time_Hours": "None",
    }

    summary = upload_and_import(client, auth_headers(), "DAILY_ACTIVITY", "Daily_Activity", [row])

    assert (summary["processed_records"], summary["failed_records"]) == (1, 0)


def test_na_text_is_kept_in_text_columns_of_the_timesheet(client, auth_headers, engine, master):
    rows = [dict(TIMESHEET[0], Client_Name="N/A")]

    upload_and_import(client, auth_headers(), "PROJECT_TIMESHEET", "Timesheet", rows)

    with Session(engine) as session:
        assert session.query(ProjectTimesheet).one().client_name == "N/A"
