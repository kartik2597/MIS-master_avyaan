from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.employee import Employee
from app.models.upload_history import UploadHistory
from app.reports.report_types import ReportType
from app.services.file_upload import build_upload_directory


UPLOAD_STATUS_VALIDATED = "VALIDATED"
UPLOAD_STATUS_PROCESSING = "PROCESSING"
UPLOAD_STATUS_COMPLETED = "COMPLETED"
UPLOAD_STATUS_FAILED = "FAILED"

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
        dataframe = read_uploaded_dataframe(resolve_uploaded_file_path(upload_history))
        total_records = len(dataframe.index)
        employees, failed_records = map_dataframe_to_employees(dataframe)
        processed_records = upsert_employees(db=db, employee_rows=employees)

        mark_upload_completed(
            db=db,
            upload_history=upload_history,
            total_records=total_records,
            processed_records=processed_records,
            failed_records=failed_records,
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
    if upload_history.upload_status != UPLOAD_STATUS_VALIDATED:
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


def read_uploaded_dataframe(file_path: Path):
    import pandas as pd

    extension = file_path.suffix.lower()
    try:
        if extension == ".csv":
            return pd.read_csv(file_path)
        if extension == ".xlsx":
            return pd.read_excel(file_path, engine="openpyxl")
        if extension == ".xls":
            return pd.read_excel(file_path, engine="xlrd")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to read uploaded file",
        ) from exc

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unsupported uploaded file extension",
    )


def map_dataframe_to_employees(dataframe) -> tuple[list[dict[str, Any]], int]:
    column_map = build_column_map(list(dataframe.columns))
    employee_rows: list[dict[str, Any]] = []
    failed_records = 0

    for _, row in dataframe.iterrows():
        try:
            employee_rows.append(map_employee_row(row=row, column_map=column_map))
        except ValueError:
            failed_records += 1

    return employee_rows, failed_records


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

    missing_fields = [
        field_name
        for field_name in REQUIRED_EMPLOYEE_FIELDS
        if is_blank(employee_data.get(field_name))
    ]
    if missing_fields:
        raise ValueError("Missing required employee fields")

    employee_data["date_of_joining"] = parse_date(employee_data["date_of_joining"])
    employee_data["emp_id"] = str(employee_data["emp_id"])
    return employee_data


def upsert_employees(db: Session, employee_rows: list[dict[str, Any]]) -> int:
    if not employee_rows:
        return 0

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
    return len(employee_rows)


def mark_upload_processing(db: Session, upload_history: UploadHistory) -> None:
    upload_history.upload_status = UPLOAD_STATUS_PROCESSING
    upload_history.processing_started_at = datetime.now()
    upload_history.processing_completed_at = None
    upload_history.error_message = None
    db.commit()
    db.refresh(upload_history)


def mark_upload_completed(
    db: Session,
    *,
    upload_history: UploadHistory,
    total_records: int,
    processed_records: int,
    failed_records: int,
) -> None:
    upload_history.upload_status = UPLOAD_STATUS_COMPLETED
    upload_history.total_records = total_records
    upload_history.processed_records = processed_records
    upload_history.failed_records = failed_records
    upload_history.processing_completed_at = datetime.now()
    upload_history.error_message = None
    db.commit()


def mark_upload_failed(
    db: Session,
    *,
    upload_history: UploadHistory,
    error_message: str,
) -> None:
    upload_history.upload_status = UPLOAD_STATUS_FAILED
    upload_history.processing_completed_at = datetime.now()
    upload_history.error_message = error_message[:1000]
    db.commit()


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


def parse_date(value: Any):
    import pandas as pd

    parsed_value = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed_value):
        raise ValueError("Invalid date_of_joining")
    return parsed_value.date()
