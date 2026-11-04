"""Value checks shared by the APR, shift adherence and shrinkage parsers.

The parsers already reject a row whose date, time or number cannot be read. These
checks catch rows that read fine but make no sense:

- a date long ago or far in the future (usually a typo such as 2062)
- negative hours, minutes, calls or counts
- a percentage below 0 or above 100
- an employee ID that is not in the employee master (optional, see below)

A row can have several problems. All of them go into one message so the Upload
History page can show "row 45: Negative staff time; Productivity % above 100".
check_report_row() raises ValueError, which the parsers already turn into a
skipped row with a reason.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.employee import Employee


EARLIEST_REPORT_DATE = date(2000, 1, 1)
# Reports are about days that have happened. A little slack covers time zones.
FUTURE_DAYS_ALLOWED = 7

# Whole-number and time fields that can never be negative. Time fields hold seconds.
NON_NEGATIVE_SUFFIXES = ("_time", "_seconds", "_minutes", "_calls", "_count", "_headcount")
NON_NEGATIVE_FIELDS = ("attrition", "employee_age_days")

# Percentage fields: 0 to 100 inclusive.
PERCENT_MARKERS = ("percent", "shrinkage")


def _label(field: str) -> str:
    return field.replace("_seconds", "").replace("_", " ")


def _is_non_negative_field(field: str) -> bool:
    return field in NON_NEGATIVE_FIELDS or field.endswith(NON_NEGATIVE_SUFFIXES)


def _is_percent_field(field: str) -> bool:
    return any(marker in field for marker in PERCENT_MARKERS)


def find_row_problems(
    row: dict[str, Any],
    known_emp_ids: set[str] | None = None,
    today: date | None = None,
) -> list[str]:
    """Every problem found in one mapped row, as short readable sentences."""
    problems: list[str] = []
    today = today or date.today()

    for field in ("report_date",):
        value = row.get(field)
        if isinstance(value, date):
            if value < EARLIEST_REPORT_DATE:
                problems.append(f"Date {value.isoformat()} is before {EARLIEST_REPORT_DATE.year}")
            elif value > today + timedelta(days=FUTURE_DAYS_ALLOWED):
                problems.append(f"Date {value.isoformat()} is in the future")

    for field, value in row.items():
        if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
            continue
        if _is_percent_field(field):
            if value < 0:
                problems.append(f"{_label(field).capitalize()} is negative ({value})")
            elif value > 100:
                problems.append(f"{_label(field).capitalize()} is above 100 ({value})")
        elif _is_non_negative_field(field) and value < 0:
            problems.append(f"Negative {_label(field)} ({value})")

    if known_emp_ids is not None:
        emp_id = str(row.get("emp_id") or "").strip()
        if emp_id and emp_id not in known_emp_ids:
            problems.append(f"Employee ID {emp_id} is not in the employee master")

    return problems


def check_report_row(
    row: dict[str, Any],
    known_emp_ids: set[str] | None = None,
    today: date | None = None,
) -> None:
    """Raise ValueError listing every problem in the row. Returns None if it is fine."""
    problems = find_row_problems(row, known_emp_ids=known_emp_ids, today=today)
    if problems:
        raise ValueError("; ".join(problems))


def load_known_emp_ids(db: Session) -> set[str] | None:
    """Employee IDs a report row may refer to, or None when the check is off.

    The check is off when APP_REJECT_UNKNOWN_EMPLOYEES is false (the default) or
    when the employee master is still empty, because then every row would fail.

    Note: reports also add the agents they mention to the employee master
    (see employee_sync), so once any report has been imported its agents count as
    "known". For a strict check, import the master database file first and keep
    this setting on.
    """
    if not settings.REJECT_UNKNOWN_EMPLOYEES:
        return None
    ids = set(db.scalars(select(Employee.emp_id)).all())
    return ids or None
