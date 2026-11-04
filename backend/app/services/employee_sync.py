"""Keep the employees table in step with the people found in uploaded reports.

APR, shift adherence, shrinkage, daily activity and shrinkage hours reports all
name the agents they cover, but only the master database and roster uploads used
to write the employees table. So an agent could be on the dashboard without
appearing in Employee Master.

sync_employees_from_report_rows() is called from the shared upsert functions of
those reports. It never overwrites what is already stored: new agents are added,
and existing ones only get blank fields filled in.

A report knows less about a person than the master database does. For the
columns a report cannot supply (email, mobile, TL, location) the new row gets an
empty string, the same as the roster import. A report with no joining date gets
the agent's first report date as a stand-in. Upload a master database file to
fill in the real details; it replaces these values.
"""

from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.employee import Employee


# Values the importers write when a report has no value for a column.
PLACEHOLDERS = {"", "n/a", "na", "none", "null", "-"}

# Stored as plain text columns: (field name, maximum length in the table).
TEXT_LIMITS = {
    "emp_id": 50,
    "employee_name": 255,
    "department": 100,
    "process": 100,
    "designation": 100,
    "manager_name": 255,
    "tl_name": 255,
    "employment_status": 50,
}

# Filled in only when the employee row is blank for them.
FILL_WHEN_BLANK = ("department", "process", "designation", "manager_name", "tl_name")


def clean_text(value: Any, limit: int) -> str:
    """Report value -> trimmed text, or "" when the report had nothing real."""
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    text = str(value).strip()
    if text.lower() in PLACEHOLDERS:
        return ""
    return text[:limit]


def summarize_report_rows(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """One merged record per emp_id. The latest non-blank value of each field wins."""
    people: dict[str, dict[str, Any]] = {}

    for row in rows:
        emp_id = clean_text(row.get("emp_id"), TEXT_LIMITS["emp_id"])
        if not emp_id:
            continue
        person = people.setdefault(
            emp_id,
            {
                "emp_id": emp_id,
                "upload_id": None,
                "first_seen": None,
                "date_of_joining": None,
                **{field: "" for field in TEXT_LIMITS if field != "emp_id"},
            },
        )

        # Reports call the team "process" or "campaign"; the table keeps both.
        team = clean_text(
            row.get("process") or row.get("campaign"), TEXT_LIMITS["process"]
        )
        found = {
            "employee_name": clean_text(row.get("employee_name"), TEXT_LIMITS["employee_name"]),
            "process": team,
            "department": clean_text(row.get("department"), TEXT_LIMITS["department"]) or team,
            "designation": clean_text(row.get("designation"), TEXT_LIMITS["designation"]),
            "manager_name": clean_text(row.get("manager_name"), TEXT_LIMITS["manager_name"]),
            "tl_name": clean_text(row.get("tl_name"), TEXT_LIMITS["tl_name"]),
            "employment_status": clean_text(
                row.get("status") or row.get("employment_status"),
                TEXT_LIMITS["employment_status"],
            ),
        }
        for field, value in found.items():
            if value:
                person[field] = value

        report_date = row.get("report_date")
        if isinstance(report_date, date) and (
            person["first_seen"] is None or report_date < person["first_seen"]
        ):
            person["first_seen"] = report_date

        joined = row.get("date_of_joining")
        if isinstance(joined, date):
            person["date_of_joining"] = joined

        if row.get("upload_id") is not None:
            person["upload_id"] = row["upload_id"]

    return people


def sync_employees_from_report_rows(
    db: Session,
    rows: list[dict[str, Any]],
    upload_id: UUID | None = None,
    *,
    commit: bool = True,
) -> int:
    """Add the agents in these report rows to the employees table.

    Returns how many new employees were created. Commits when it changed
    anything; with commit=False it only flushes, so the caller decides.
    """
    people = summarize_report_rows(rows)
    if not people:
        return 0

    existing = {
        employee.emp_id: employee
        for employee in db.scalars(
            select(Employee).where(Employee.emp_id.in_(list(people)))
        ).all()
    }

    created = 0
    changed = False
    for emp_id, person in people.items():
        employee = existing.get(emp_id)

        if employee is None:
            joined = person["date_of_joining"] or person["first_seen"] or date.today()
            db.add(
                Employee(
                    upload_id=person["upload_id"] or upload_id,
                    emp_id=emp_id,
                    employee_name=person["employee_name"] or emp_id,
                    email="",
                    mobile="",
                    department=person["department"],
                    process=person["process"],
                    designation=person["designation"],
                    manager_name=person["manager_name"],
                    tl_name=person["tl_name"],
                    date_of_joining=joined,
                    employment_status=person["employment_status"] or "Active",
                    location="",
                )
            )
            created += 1
            changed = True
            continue

        # Known employee: never overwrite, only fill what is still empty.
        for field in FILL_WHEN_BLANK:
            if not getattr(employee, field) and person[field]:
                setattr(employee, field, person[field])
                changed = True

    if changed:
        if commit:
            db.commit()
        else:
            db.flush()
    return created
