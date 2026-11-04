from app.models.upload_history import UploadHistory
from app.schemas.upload_history import RowErrorItem, UploadValidationReport


def build_validation_report(upload: UploadHistory) -> UploadValidationReport:
    """Columns first, then the rows an import skipped, for one upload."""
    result = upload.validation_result or {}
    stored_errors = upload.row_errors or []
    row_errors = [
        RowErrorItem(row=int(item.get("row", 0)), reason=str(item.get("reason", "")))
        for item in stored_errors
        if isinstance(item, dict)
    ]
    return UploadValidationReport(
        upload_id=upload.id,
        original_file_name=upload.original_file_name,
        report_type=upload.report_type,
        upload_status=upload.upload_status,
        uploaded_by_name=upload.uploaded_by_name,
        uploaded_at=upload.uploaded_at,
        sheet_name=result.get("sheet_name"),
        columns_valid=result.get("valid"),
        validation_score=result.get("validation_score"),
        missing_columns=result.get("missing_columns") or [],
        extra_columns=result.get("extra_columns") or [],
        total_records=upload.total_records,
        processed_records=upload.processed_records,
        failed_records=upload.failed_records,
        error_message=upload.error_message,
        row_errors=row_errors,
        row_errors_truncated=upload.failed_records > len(row_errors),
    )
