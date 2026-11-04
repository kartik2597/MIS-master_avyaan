import logging
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.employee import Employee
from app.models.upload_history import UploadHistory
from app.parsers.upload_status import (
    RowError,
    mark_upload_completed,
    mark_upload_failed,
    mark_upload_processing,
)
from app.reports.report_types import ReportType
from app.services.file_upload import READ_OPTIONS, build_upload_directory, is_importable


logger = logging.getLogger(__name__)

EMPLOYEE_COLUMN_ALIASES = {
    "emp_id": ["emp_id", "emp id", "employee id", "employee_id", "Employee ID"],
    "employee_name": ["employee_name", "employee name", "Employee Name"],
    "email": ["email", "Email"],
    "mobile": ["mobile", "Mobile", "mobile number", "Mobile Number"],
    "department": ["department", "Department"],
    "process": ["process", "Process"],
    "designation": ["designation", "Designation"],
    "manager_name": ["manager_name", "manager name", "Manager Name"],
    "tl_name": ["tl_name", "tl name", "TL Name", "team lead", "Team Lead"],
    "date_of_joining": [
        "date_of_joining",
        "date of joining",
        "Date Of Joining",
        "DOJ",
    ],
    "employment_status": [
        "employment_status",
        "employment status",
        "Employment Status",
        "status",
        "Status",
    ],
    "location": ["location", "Location"],
}

REQUIRED_EMPLOYEE_FIELDS = set(EMPLOYEE_COLUMN_ALIASES.keys())


def import_master_database(db: Session, upload_id: UUID) -> dict[str, int]:
    upload_history = get_upload_for_import(db=db, upload_id=upload_id)
    mark_upload_processing(db=db, upload_history=upload_history)

    try:
        # A workbook can hold several reports; open the sheet this upload came from.
        sheet_name = (upload_history.validation_result or {}).get("sheet_name")
        dataframe = read_uploaded_dataframe(
            resolve_uploaded_file_path(upload_history), sheet_name
        )
        total_records = len(dataframe.index)
        ensure_required_columns(list(dataframe.columns))
        employees, row_errors = map_dataframe_to_employees(dataframe)
        for employee_row in employees:
            employee_row["upload_id"] = upload_id
        processed_records = upsert_employees(db=db, employee_rows=employees)
        # Rows dropped as duplicates of an earlier emp_id count as failed.
        duplicate_rows = len(employees) - processed_records
        failed_records = len(row_errors) + duplicate_rows
        if duplicate_rows:
            row_errors.append(
                (0, f"{duplicate_rows} duplicate Employee ID row(s); the last one was kept")
            )

        mark_upload_completed(
            db=db,
            upload_history=upload_history,
            total_records=total_records,
            processed_records=processed_records,
            failed_records=failed_records,
            row_errors=row_errors,
        )
        return {
            "total_records": total_records,
            "processed_records": processed_records,
            "failed_records": failed_records,
        }
    except Exception as exc:
        db.rollback()
        mark_upload_failed(db=db, upload_history=upload_history, error_message=str(exc))
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Master database import failed",
        ) from exc


def get_upload_for_import(db: Session, upload_id: UUID) -> UploadHistory:
    upload_history = db.get(UploadHistory, upload_id)
    if upload_history is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload history not found",
        )
    if upload_history.report_type != ReportType.MASTER_DATABASE.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload is not a MASTER_DATABASE report",
        )
    if not is_importable(upload_history):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload must be validated before import",
        )
    return upload_history


def resolve_uploaded_file_path(upload_history: UploadHistory) -> Path:
    upload_directory = build_upload_directory(upload_history.uploaded_at)
    file_path = upload_directory / upload_history.file_name
    if file_path.exists():
        return file_path

    storage_uploads_path = settings.STORAGE_PATH / "uploads"
    fallback_matches = list(storage_uploads_path.rglob(upload_history.file_name))
    if fallback_matches:
        return fallback_matches[0]

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Uploaded file not found in storage",
    )


def read_uploaded_dataframe(file_path: Path, sheet_name: str | None = None):
    import pandas as pd

    extension = file_path.suffix.lower()
    sheet = sheet_name if sheet_name is not None else 0
    try:
        if extension == ".csv":
            return pd.read_csv(file_path, **READ_OPTIONS)
        if extension == ".xlsx":
            return pd.read_excel(file_path, sheet_name=sheet, engine="openpyxl", **READ_OPTIONS)
        if extension == ".xls":
            return pd.read_excel(file_path, sheet_name=sheet, engine="xlrd", **READ_OPTIONS)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to read uploaded file",
        ) from exc

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unsupported uploaded file extension",
    )


def ensure_required_columns(uploaded_columns: list[str]) -> None:
    column_map = build_column_map(uploaded_columns)
    missing_fields = sorted(REQUIRED_EMPLOYEE_FIELDS - set(column_map))
    if missing_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Master database file is missing columns for: "
            + ", ".join(missing_fields),
        )


def map_dataframe_to_employees(
    dataframe,
) -> tuple[list[dict[str, Any]], list[RowError]]:
    column_map = build_column_map(list(dataframe.columns))
    employee_rows: list[dict[str, Any]] = []
    row_errors: list[RowError] = []

    for row_number, (_, row) in enumerate(dataframe.iterrows(), start=2):
        try:
            employee_rows.append(map_employee_row(row=row, column_map=column_map))
        except ValueError as exc:
            # row_number is the spreadsheet row (row 1 is the header).
            logger.warning("Master database row %s skipped: %s", row_number, exc)
            row_errors.append((row_number, str(exc)))

    return employee_rows, row_errors


def build_column_map(uploaded_columns: list[str]) -> dict[str, str]:
    normalized_columns = {
        normalize_column(column): column for column in uploaded_columns
    }
    column_map: dict[str, str] = {}

    for field_name, aliases in EMPLOYEE_COLUMN_ALIASES.items():
        for alias in aliases:
            normalized_alias = normalize_column(alias)
            if normalized_alias in normalized_columns:
                column_map[field_name] = normalized_columns[normalized_alias]
                break

    return column_map


def map_employee_row(row, column_map: dict[str, str]) -> dict[str, Any]:
    employee_data = {
        field_name: clean_value(row[column_name])
        for field_name, column_name in column_map.items()
    }

    missing_fields = sorted(
        field_name
        for field_name in REQUIRED_EMPLOYEE_FIELDS
        if is_blank(employee_data.get(field_name))
    )
    if missing_fields:
        raise ValueError("Missing required employee fields: " + ", ".join(missing_fields))

    employee_data["date_of_joining"] = parse_date(employee_data["date_of_joining"])
    # Every other column is text in the database. Excel hands numeric cells
    # (Mobile, Employee ID) back as numpy numbers, which the database driver
    # cannot write into a text column, so convert them here.
    for field_name in list(employee_data):
        if field_name != "date_of_joining":
            employee_data[field_name] = to_text(employee_data[field_name])
    return employee_data


def upsert_employees(db: Session, employee_rows: list[dict[str, Any]]) -> int:
    if not employee_rows:
        return 0

    # Later rows win when the same emp_id appears more than once.
    unique_employee_rows = {
        row["emp_id"]: row for row in employee_rows
    }
    emp_ids = list(unique_employee_rows.keys())
    existing_employees = {
        employee.emp_id: employee
        for employee in db.scalars(
            select(Employee).where(Employee.emp_id.in_(emp_ids))
        ).all()
    }
    new_employees: list[Employee] = []

    for employee_data in unique_employee_rows.values():
        existing_employee = existing_employees.get(employee_data["emp_id"])
        if existing_employee is None:
            new_employees.append(Employee(**employee_data))
            continue

        for field_name, value in employee_data.items():
            setattr(existing_employee, field_name, value)

    if new_employees:
        db.add_all(new_employees)
    db.commit()
    return len(unique_employee_rows)


def normalize_column(column_name: str) -> str:
    return " ".join(str(column_name).strip().lower().replace("_", " ").split())


def clean_value(value: Any) -> Any:
    import pandas as pd

    if pd.isna(value):
        return None
    if isinstance(value, str):
        return value.strip()
    return value


def is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def to_text(value: Any) -> str:
    """Turn a cell into clean text: numpy numbers become plain Python, and a
    whole number read as a float (9876543210.0) loses its ".0"."""
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value).strip()


def parse_date(value: Any):
    import pandas as pd

    parsed_value = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed_value):
        raise ValueError("Invalid date_of_joining")
    return parsed_value.date()
