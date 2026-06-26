import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.upload_history import UploadHistory
from app.models.user import User
from app.reports.detector import detect_report_type
from app.reports.detector.service import DetectionResult
from app.reports.schemas import ReportValidationResult
from app.reports.validators import validate_uploaded_report
from app.services.raw_report_records import save_raw_report_rows


ALLOWED_UPLOAD_EXTENSIONS = {".xlsx", ".xls", ".csv"}
UPLOAD_STATUS_PENDING = "PENDING"
UPLOAD_STATUS_VALIDATED = "VALIDATED"
UPLOAD_STATUS_FAILED = "FAILED"
UNKNOWN_REPORT_TYPE = "UNKNOWN"


def validate_upload_extension(file_name: str) -> str:
    extension = Path(file_name).suffix.lower()
    if extension not in ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .xlsx, .xls, and .csv files are allowed",
        )
    return extension


def build_upload_directory(uploaded_at: datetime | None = None) -> Path:
    timestamp = uploaded_at or datetime.now()
    return (
        settings.STORAGE_PATH
        / "uploads"
        / f"{timestamp:%Y}"
        / f"{timestamp:%m}"
        / f"{timestamp:%d}"
    )


def generate_unique_file_name(original_file_name: str) -> str:
    extension = validate_upload_extension(original_file_name)
    return f"{uuid.uuid4().hex}{extension}"


def save_upload_file(upload_file: UploadFile, destination: Path) -> int:
    destination.parent.mkdir(parents=True, exist_ok=True)
    upload_file.file.seek(0)

    with destination.open("wb") as output_file:
        shutil.copyfileobj(upload_file.file, output_file)

    upload_file.file.seek(0)
    return destination.stat().st_size


def read_uploaded_headers(file_path: Path) -> list[str]:
    import pandas as pd

    extension = file_path.suffix.lower()
    try:
        if extension == ".csv":
            dataframe = pd.read_csv(file_path, nrows=0)
        elif extension == ".xlsx":
            dataframe = pd.read_excel(file_path, nrows=0, engine="openpyxl")
        elif extension == ".xls":
            dataframe = pd.read_excel(file_path, nrows=0, engine="xlrd")
        else:
            raise ValueError("Unsupported file extension")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to read file headers",
        ) from exc

    return [str(column) for column in dataframe.columns]


def read_uploaded_rows(file_path: Path) -> list[dict[str, Any]]:
    import pandas as pd

    extension = file_path.suffix.lower()
    try:
        if extension == ".csv":
            dataframe = pd.read_csv(file_path)
        elif extension == ".xlsx":
            dataframe = pd.read_excel(file_path, engine="openpyxl")
        elif extension == ".xls":
            dataframe = pd.read_excel(file_path, engine="xlrd")
        else:
            raise ValueError("Unsupported file extension")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to read uploaded file",
        ) from exc

    return json.loads(dataframe.to_json(orient="records", date_format="iso"))


def create_pending_upload_history(
    db: Session,
    *,
    original_file_name: str,
    file_name: str,
    file_size: int,
    uploaded_by: User,
    detection: DetectionResult,
) -> UploadHistory:
    upload_history = UploadHistory(
        file_name=file_name,
        original_file_name=original_file_name,
        report_type=detection.detected_report_type or UNKNOWN_REPORT_TYPE,
        file_size=file_size,
        uploaded_by=uploaded_by.id,
        upload_status=UPLOAD_STATUS_PENDING,
        total_records=0,
        processed_records=0,
        failed_records=0,
        error_message=None,
        validation_result=None,
    )
    db.add(upload_history)
    db.commit()
    db.refresh(upload_history)
    return upload_history


def upload_and_detect_report(
    db: Session,
    *,
    upload_file: UploadFile,
    uploaded_by: User,
) -> tuple[UploadHistory, DetectionResult, ReportValidationResult, int]:
    if not upload_file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a file name",
        )

    validate_upload_extension(upload_file.filename)
    stored_file_name = generate_unique_file_name(upload_file.filename)
    destination = build_upload_directory() / stored_file_name
    file_size = save_upload_file(upload_file, destination)
    uploaded_columns = read_uploaded_headers(destination)
    detection = detect_report_type(uploaded_columns)
    upload_history = create_pending_upload_history(
        db=db,
        original_file_name=upload_file.filename,
        file_name=stored_file_name,
        file_size=file_size,
        uploaded_by=uploaded_by,
        detection=detection,
    )
    validation_result = validate_detected_upload(
        detection=detection,
        uploaded_columns=uploaded_columns,
    )
    raw_rows = read_uploaded_rows(destination)
    save_raw_report_rows(
        db=db,
        upload_id=upload_history.id,
        report_type=upload_history.report_type,
        rows=raw_rows,
    )
    update_upload_validation_result(
        db=db,
        upload_history=upload_history,
        validation_result=validation_result,
        total_records=len(raw_rows),
    )

    return upload_history, detection, validation_result, len(uploaded_columns)


def validate_detected_upload(
    *,
    detection: DetectionResult,
    uploaded_columns: list[str],
) -> ReportValidationResult:
    if detection.detected_report_type is None:
        return ReportValidationResult(
            valid=False,
            missing_columns=[],
            extra_columns=uploaded_columns,
            validation_score=0,
        )
    return validate_uploaded_report(
        report_type=detection.detected_report_type,
        uploaded_columns=uploaded_columns,
    )


def update_upload_validation_result(
    db: Session,
    *,
    upload_history: UploadHistory,
    validation_result: ReportValidationResult,
    total_records: int,
) -> UploadHistory:
    upload_history.validation_result = validation_result.model_dump(mode="json")
    upload_history.upload_status = (
        UPLOAD_STATUS_VALIDATED if validation_result.valid else UPLOAD_STATUS_FAILED
    )
    upload_history.total_records = total_records
    upload_history.error_message = (
        None
        if validation_result.valid
        else "Required columns are missing or report type could not be validated"
    )
    db.commit()
    db.refresh(upload_history)
    return upload_history
