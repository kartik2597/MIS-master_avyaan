"""Add agents from reports uploaded BEFORE the employee sync existed to Employee Master.

Reports imported earlier put their agents on the dashboard but never in the
employees table. Run once:

    python backfill_employees.py            # preview only, changes nothing
    python backfill_employees.py --apply    # write the changes

It reads the APR, shift adherence and shrinkage report tables (which also hold
daily activity and shrinkage hours data) and adds every agent that is missing
from the employees table. Existing employees are never overwritten; only blank
process / designation / manager fields are filled in.

New rows have no email, mobile, TL or location (reports do not carry them).
Upload a master database file afterwards to fill those in.
"""
import argparse

from sqlalchemy import func, select

from app.database.session import SessionLocal
from app.models.agent_daily_performance import AgentDailyPerformance
from app.models.agent_shift_adherence import AgentShiftAdherence
from app.models.agent_shrinkage import AgentShrinkage
from app.models.employee import Employee
from app.services.employee_sync import sync_employees_from_report_rows


# Columns each report table can contribute (all are optional in the sync).
SOURCES = [
    (
        AgentDailyPerformance,
        ("emp_id", "employee_name", "report_date", "campaign", "upload_id"),
    ),
    (
        AgentShiftAdherence,
        (
            "emp_id",
            "employee_name",
            "report_date",
            "status",
            "process",
            "designation",
            "manager_name",
            "upload_id",
        ),
    ),
    (
        AgentShrinkage,
        (
            "emp_id",
            "employee_name",
            "report_date",
            "status",
            "process",
            "designation",
            "manager_name",
            "date_of_joining",
            "upload_id",
        ),
    ),
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="write the changes")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        before = db.scalar(select(func.count()).select_from(Employee)) or 0

        for model, columns in SOURCES:
            attributes = [getattr(model, name) for name in columns]
            # Oldest first, so the newest report's values win.
            records = db.execute(
                select(*attributes).order_by(model.report_date.asc())
            ).all()
            rows = [dict(zip(columns, record)) for record in records]
            created = sync_employees_from_report_rows(db, rows, commit=False)
            print(f"{model.__tablename__}: {len(rows)} rows read, {created} employee(s) added")

        after = db.scalar(select(func.count()).select_from(Employee)) or 0
        print(f"Employees: {before} -> {after}")

        if args.apply:
            db.commit()
            print("Changes saved.")
        else:
            db.rollback()
            print("Preview only. Nothing was changed. Re-run with --apply to save.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
