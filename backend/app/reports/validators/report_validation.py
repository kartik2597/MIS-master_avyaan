from collections.abc import Iterable

from app.reports.registry import get_report_definition
from app.reports.report_types import ReportType
from app.reports.schemas import ReportValidationResult
from app.reports.validators.columns import normalize_column_name


def validate_uploaded_report(
    report_type: ReportType | str,
    uploaded_columns: Iterable[str],
) -> ReportValidationResult:
    report_definition = get_report_definition(report_type)
    normalized_uploaded_columns = {
        normalize_column_name(column): column for column in uploaded_columns
    }
    allowed_columns = {
        normalize_column_name(column)
        for column in [
            *report_definition.required_columns,
            *report_definition.optional_columns,
        ]
    }

    missing_columns = [
        column
        for column in report_definition.required_columns
        if normalize_column_name(column) not in normalized_uploaded_columns
    ]
    extra_columns = [
        original_column
        for normalized_column, original_column in normalized_uploaded_columns.items()
        if normalized_column not in allowed_columns
    ]
    matched_required_columns = (
        len(report_definition.required_columns) - len(missing_columns)
    )

    return ReportValidationResult(
        valid=not missing_columns,
        missing_columns=missing_columns,
        extra_columns=extra_columns,
        validation_score=calculate_validation_score(
            matched_required_columns=matched_required_columns,
            total_required_columns=len(report_definition.required_columns),
        ),
    )


def calculate_validation_score(
    *,
    matched_required_columns: int,
    total_required_columns: int,
) -> int:
    if total_required_columns == 0:
        return 0
    return round((matched_required_columns / total_required_columns) * 100)

