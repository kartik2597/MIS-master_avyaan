"""Find and remove fake / test rows from the three report tables.

Run from the backend folder. By default NOTHING is deleted: it only prints a
summary so you can decide what to remove.

  python clean_report_data.py
      Row counts per report date for each table, plus agent IDs that are in the
      reports but NOT in the Employee Master (the usual sign of fake data).

  python clean_report_data.py --unknown-agents
  python clean_report_data.py --date 2026-04-01 --date 2026-04-02
      Show what WOULD be deleted (dry run).

  python clean_report_data.py --unlinked
      Dry run: rows that belong to no upload in Upload History (leftovers from
      uploads deleted before delete-with-data was fixed). Run
      backfill_upload_ids.py --apply first so real data is linked, not lost.

  python clean_report_data.py --unknown-agents --apply
      Actually delete. Combine --unknown-agents, --unlinked and --date freely.
"""
import argparse
from datetime import date

from sqlalchemy import delete, func, or_, select

from app.database.session import SessionLocal
from app.models.agent_daily_performance import AgentDailyPerformance
from app.models.agent_shift_adherence import AgentShiftAdherence
from app.models.agent_shrinkage import AgentShrinkage
from app.models.employee import Employee

MODELS = (AgentDailyPerformance, AgentShiftAdherence, AgentShrinkage)


def print_summary(db) -> None:
    known_ids = set(db.scalars(select(Employee.emp_id)).all())
    print(f"Employee Master has {len(known_ids)} employees.\n")
    for model in MODELS:
        print(f"== {model.__tablename__} ==")
        rows = db.execute(
            select(model.report_date, func.count())
            .group_by(model.report_date)
            .order_by(model.report_date)
        ).all()
        for report_date, count in rows:
            print(f"  {report_date}: {count} rows")
        if not rows:
            print("  (empty)")
        unknown = sorted(
            set(db.scalars(select(model.emp_id).distinct()).all()) - known_ids
        )
        print(f"  agent IDs not in Employee Master: {len(unknown)}")
        if unknown:
            print("   ", ", ".join(unknown[:30]), "..." if len(unknown) > 30 else "")
        print()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--unknown-agents", action="store_true",
                        help="rows whose emp_id is not in the Employee Master")
    parser.add_argument("--unlinked", action="store_true",
                        help="rows that belong to no upload in Upload History (upload_id is empty)")
    parser.add_argument("--date", action="append", default=[],
                        help="delete every row for this report date (YYYY-MM-DD)")
    parser.add_argument("--all", action="store_true",
                        help="delete EVERY row in the three report tables (dashboard goes empty)")
    parser.add_argument("--uploads", action="store_true",
                        help="with --all: also clear raw records and upload history")
    parser.add_argument("--employees", action="store_true",
                        help="delete EVERY employee from the Employee Master (can be combined with --all)")
    parser.add_argument("--apply", action="store_true",
                        help="really delete (default is a dry run)")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if (
            not args.unknown_agents
            and not args.unlinked
            and not args.date
            and not args.all
            and not args.employees
        ):
            print_summary(db)
            return

        if args.all or args.employees:
            total = 0
            if args.all:
                for model in MODELS:
                    count = db.scalar(select(func.count()).select_from(model)) or 0
                    total += count
                    print(f"{model.__tablename__}: {count} rows")
                    if args.apply and count:
                        db.execute(delete(model))
            if args.employees:
                count = db.scalar(select(func.count()).select_from(Employee)) or 0
                total += count
                print(f"{Employee.__tablename__}: {count} rows")
                if args.apply and count:
                    db.execute(delete(Employee))
            if args.all and args.uploads:
                from app.models.raw_report_record import RawReportRecord
                from app.models.upload_history import UploadHistory

                for model in (RawReportRecord, UploadHistory):
                    count = db.scalar(select(func.count()).select_from(model)) or 0
                    total += count
                    print(f"{model.__tablename__}: {count} rows")
                    if args.apply and count:
                        db.execute(delete(model))
            if args.apply:
                db.commit()
                print(f"\nDeleted {total} rows.")
            else:
                print(f"\nDry run: {total} rows would be deleted. Add --apply to delete.")
            return

        dates = [date.fromisoformat(d) for d in args.date]
        known_ids = set(db.scalars(select(Employee.emp_id)).all())
        if args.unknown_agents and not known_ids:
            raise SystemExit("Employee Master is empty; refusing to treat every agent as unknown.")

        total = 0
        for model in MODELS:
            conditions = []
            if args.unknown_agents:
                conditions.append(model.emp_id.not_in(known_ids))
            if args.unlinked:
                conditions.append(model.upload_id.is_(None))
            if dates:
                conditions.append(model.report_date.in_(dates))
            where = or_(*conditions)
            count = db.scalar(select(func.count()).select_from(model).where(where)) or 0
            total += count
            print(f"{model.__tablename__}: {count} rows match")
            if args.apply and count:
                db.execute(delete(model).where(where))

        if args.apply:
            db.commit()
            print(f"\nDeleted {total} rows.")
        else:
            print(f"\nDry run: {total} rows would be deleted. Add --apply to delete.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
