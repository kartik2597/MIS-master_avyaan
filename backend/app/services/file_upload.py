import hashlib
import json
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.raw_report_record import RawReportRecord
from app.models.upload_history import UploadHistory
from app.models.user import User
from app.reports.detector import detect_report_type
from app.reports.detector.service import DetectionResult
from app.reports.report_types import ReportType
from app.reports.schemas import ReportValidationResult
from app.reports.validators import validate_uploaded_report
from app.services.raw_report_records import save_raw_report_rows


ALLOWED_UPLOAD_EXTENSIONS = {".xlsx", ".xls", ".csv"}
UPLOAD_STATUS_PENDING = "PENDING"
UPLOAD_STATUS_VALIDATED = "VALIDATED"
UPLOAD_STATUS_FAILED = "FAILED"
UNKNOWN_REPORT_TYPE = "UNKNOWN"
UPLOAD_CHUNK_SIZE = 1024 * 1024
# An earlier upload of the same file in one of these states blocks a re-upload.
# A FAILED one does not: the person may be retrying after fixing the problem.
DUPLICATE_BLOCKING_STATUSES = ("VALIDATED", "PROCESSING", "COMPLETED")


@dataclass
class SheetUpload:
    """One report found in an uploaded file (one sheet of a workbook, or a CSV)."""

    upload_history: UploadHistory
    detection: DetectionResult
    validation_result: ReportValidationResult
    total_columns: int
    sheet_name: str | None


@dataclass
class WorkbookUpload:
    sheets: list[SheetUpload]
    # Sheets that matched no report type (notes, metric guides...) and were skipped.
    ignored_sheets: list[str]


def has_importer(report_type: str) -> bool:
    """Whether an importer exists for this report type.

    Some report types can be detected and validated but have no importer yet.
    The importer table lives with the import routes, so it is imported here to
    avoid a circular import.
    """
    from app.api.routes.imports import IMPORTERS

    try:
        return ReportType(report_type) in IMPORTERS
    except ValueError:
        return False


def is_importable(upload_history: UploadHistory) -> bool:
    """Whether an upload may be (re)imported.

    A VALIDATED upload can be imported. An upload whose import failed is also
    marked FAILED, but its file passed validation, so it can be retried. An upload
    that failed validation (missing columns) can never be imported.
    """
    if upload_history.upload_status == UPLOAD_STATUS_VALIDATED:
        return True
    if upload_history.upload_status == UPLOAD_STATUS_FAILED:
        validation_result = upload_history.validation_result or {}
        return validation_result.get("valid") is True
    return False


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


def compute_file_hash(file_path: Path) -> str:
    """SHA-256 of a stored file, read in chunks so large files stay out of memory."""
    digest = hashlib.sha256()
    with file_path.open("rb") as stored_file:
        while chunk := stored_file.read(UPLOAD_CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def find_duplicate_upload(db: Session, file_hash: str) -> UploadHistory | None:
    """The most recent live upload of exactly this file, if there is one."""
    return db.scalars(
        select(UploadHistory)
        .where(
            UploadHistory.file_hash == file_hash,
            UploadHistory.upload_status.in_(DUPLICATE_BLOCKING_STATUSES),
        )
        .order_by(UploadHistory.uploaded_at.desc())
        .limit(1)
    ).first()


def describe_duplicate_upload(duplicate: UploadHistory) -> str:
    uploaded_at = duplicate.uploaded_at
    when = f" on {uploaded_at:%d %b %Y at %H:%M}" if uploaded_at else ""
    state = duplicate.upload_status.replace("_", " ").lower()
    return (
        f"This exact file was already uploaded as '{duplicate.original_file_name}'"
        f"{when} (status: {state}). Upload it again only if you want to reprocess it."
    )


def save_upload_file(upload_file: UploadFile, destination: Path) -> int:
    destination.parent.mkdir(parents=True, exist_ok=True)
    upload_file.file.seek(0)

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    written_bytes = 0
    try:
        with destination.open("wb") as output_file:
            while chunk := upload_file.file.read(UPLOAD_CHUNK_SIZE):
                written_bytes += len(chunk)
                if written_bytes > max_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File is larger than {settings.MAX_UPLOAD_SIZE_MB} MB",
                    )
                output_file.write(chunk)
    except Exception:
        destination.unlink(missing_ok=True)
        raise

    upload_file.file.seek(0)
    return written_bytes


def read_workbook_headers(file_path: Path) -> list[tuple[str | None, list[str]]]:
    """Headers of every sheet as (sheet name, columns). A CSV has one unnamed sheet."""
    import pandas as pd

    extension = file_path.suffix.lower()
    try:
        if extension == ".csv":
            dataframe = pd.read_csv(file_path, nrows=0)
            return [(None, [str(column) for column in dataframe.columns])]
        if extension == ".xlsx":
            sheets = pd.read_excel(file_path, sheet_name=None, nrows=0, engine="openpyxl")
        elif extension == ".xls":
            sheets = pd.read_excel(file_path, sheet_name=None, nrows=0, engine="xlrd")
        else:
            raise ValueError("Unsupported file extension")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to read file headers",
        ) from exc

    return [
        (str(name), [str(column) for column in dataframe.columns])
        for name, dataframe in sheets.items()
    ]


def read_uploaded_headers(file_path: Path) -> list[str]:
    """Headers of the first sheet (kept for callers that only care about one)."""
    sheets = read_workbook_headers(file_path)
    return sheets[0][1] if sheets else []


# pandas turns "NA", "N/A", "None" and "null" into empty cells by default, which
# lost real values (a TL named "NA"). Only a truly empty cell is blank; the number,
# time and date parsers still treat NA-like text as blank (parsers.utils.null_if_na).
READ_OPTIONS = {"keep_default_na": False, "na_values": [""]}


def read_uploaded_rows(
    file_path: Path,
    sheet_name: str | None = None,
) -> list[dict[str, Any]]:
    import pandas as pd

    extension = file_path.suffix.lower()
    sheet = sheet_name if sheet_name is not None else 0
    try:
        if extension == ".csv":
            dataframe = pd.read_csv(file_path, **READ_OPTIONS)
        elif extension == ".xlsx":
            dataframe = pd.read_excel(file_path, sheet_name=sheet, engine="openpyxl", **READ_OPTIONS)
        elif extension == ".xls":
            dataframe = pd.read_excel(file_path, sheet_name=sheet, engine="xlrd", **READ_OPTIONS)
        else:
            raise ValueError("Unsupported file extension")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to read uploaded file",
        ) from exc

    # Fully blank rows (spacing, trailing formatting) are not records.
    dataframe = dataframe.dropna(how="all")
    return json.loads(dataframe.to_json(orient="records", date_format="iso"))


def create_pending_upload_history(
    db: Session,
    *,
    original_file_name: str,
    file_name: str,
    file_size: int,
    file_hash: str | None = None,
    uploaded_by: User,
    detection: DetectionResult,
) -> UploadHistory:
    upload_history = UploadHistory(
        file_name=file_name,
        original_file_name=original_file_name,
        report_type=detection.detected_report_type or UNKNOWN_REPORT_TYPE,
        file_size=file_size,
        file_hash=file_hash,
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


def upload_and_detect_workbook(
    db: Session,
    *,
    upload_file: UploadFile,
    uploaded_by: User,
    allow_duplicate: bool = False,
) -> WorkbookUpload:
    """Store the file, then detect and validate every sheet in it.

    - A file identical to one already uploaded (and not failed) is rejected with
      409 unless allow_duplicate is set, so the same report is not processed twice
      by accident.
    - Each sheet that matches a known report type becomes its own upload record,
      so one workbook can carry several reports (roster, activity, shrinkage...).
    - Sheets that match nothing are skipped when at least one other sheet matched.
    - If nothing matches, the first sheet is recorded as an UNKNOWN upload so the
      user still sees why the file was rejected.
    """
    if not upload_file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a file name",
        )

    validate_upload_extension(upload_file.filename)
    stored_file_name = generate_unique_file_name(upload_file.filename)
    destination = build_upload_directory() / stored_file_name
    file_size = save_upload_file(upload_file, destination)
    file_hash = compute_file_hash(destination)
    if not allow_duplicate:
        duplicate = find_duplicate_upload(db, file_hash)
        if duplicate is not None:
            destination.unlink(missing_ok=True)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=describe_duplicate_upload(duplicate),
            )
    created_upload_ids: list[uuid.UUID] = []

    try:
        sheet_headers = read_workbook_headers(destination)
        if not sheet_headers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The file has no sheets",
            )

        detections = [
            (sheet_name, headers, detect_report_type(headers))
            for sheet_name, headers in sheet_headers
        ]
        recognised = [item for item in detections if item[2].detected_report_type]
        if recognised:
            chosen = recognised
            ignored_sheets = [
                sheet_name
                for sheet_name, _, detection in detections
                if sheet_name is not None and not detection.detected_report_type
            ]
        else:
            chosen = detections[:1]
            ignored_sheets = []

        sheets: list[SheetUpload] = []
        for sheet_name, headers, detection in chosen:
            upload_history = create_pending_upload_history(
                db=db,
                original_file_name=upload_file.filename,
                file_name=stored_file_name,
                file_size=file_size,
                file_hash=file_hash,
                uploaded_by=uploaded_by,
                detection=detection,
            )
            created_upload_ids.append(upload_history.id)
            validation_result = validate_detected_upload(
                detection=detection,
                uploaded_columns=headers,
            )
            raw_rows = read_uploaded_rows(destination, sheet_name)
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
                sheet_name=sheet_name,
            )
            sheets.append(
                SheetUpload(
                    upload_history=upload_history,
                    detection=detection,
                    validation_result=validation_result,
                    total_columns=len(headers),
                    sheet_name=sheet_name,
                )
            )
    except Exception:
        if not created_upload_ids:
            cleanup_failed_upload(db=db, destination=destination, upload_id=None)
        for upload_id in created_upload_ids:
            cleanup_failed_upload(db=db, destination=destination, upload_id=upload_id)
        raise

    return WorkbookUpload(sheets=sheets, ignored_sheets=ignored_sheets)


def upload_and_detect_report(
    db: Session,
    *,
    upload_file: UploadFile,
    uploaded_by: User,
) -> tuple[UploadHistory, DetectionResult, ReportValidationResult, int]:
    """Single-report view of an upload: the first report found in the file."""
    outcome = upload_and_detect_workbook(
        db=db, upload_file=upload_file, uploaded_by=uploaded_by
    )
    first = outcome.sheets[0]
    return (
        first.upload_history,
        first.detection,
        first.validation_result,
        first.total_columns,
    )


def cleanup_failed_upload(
    db: Session,
    *,
    destination: Path,
    upload_id: uuid.UUID | None,
) -> None:
    """Remove the stored file and any half-created records after a failed upload."""
    db.rollback()
    destination.unlink(missing_ok=True)
    if upload_id is None:
        return

    try:
        db.execute(delete(RawReportRecord).where(RawReportRecord.upload_id == upload_id))
        db.execute(delete(UploadHistory).where(UploadHistory.id == upload_id))
        db.commit()
    except Exception:
        db.rollback()


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
    sheet_name: str | None = None,
) -> UploadHistory:
    # The sheet name rides along in the stored result so importers that read the
    # original file (the master database importer) open the right sheet.
    stored_result = validation_result.model_dump(mode="json")
    stored_result["sheet_name"] = sheet_name
    upload_history.validation_result = stored_result
    # A file can be valid for a report type that has no importer yet. It must not
    # sit at VALIDATED forever, so say plainly that it cannot be imported.
    unsupported = validation_result.valid and not has_importer(upload_history.report_type)
    upload_history.upload_status = (
        UPLOAD_STATUS_VALIDATED
        if validation_result.valid and not unsupported
        else UPLOAD_STATUS_FAILED
    )
    upload_history.total_records = total_records
    if not validation_result.valid:
        upload_history.error_message = (
            "Required columns are missing or report type could not be validated"
        )
    elif unsupported:
        upload_history.error_message = (
            f"{upload_history.report_type} reports are recognised, but importing "
            "them is not supported yet."
        )
    else:
        upload_history.error_message = None
    db.commit()
    db.refresh(upload_history)
    return upload_history
