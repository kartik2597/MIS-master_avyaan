from collections.abc import Iterable

from app.reports.headers import map_uploaded_columns, normalize_column_name
from app.reports.registry import get_header_lookup, get_report_definition
from app.reports.report_types import ReportType
from app.reports.schemas import ReportValidationResult


def validate_uploaded_report(
    report_type: ReportType | str,
    uploaded_columns: Iterable[str],
) -> ReportValidationResult:
    report_definition = get_report_definition(report_type)
    lookup = get_header_lookup(report_type)
    uploaded_columns = [str(column) for column in uploaded_columns]

    matched_canonical = set(map_uploaded_columns(uploaded_columns, lookup).values())

    missing_columns = [
        column
        for column in report_definition.required_columns
        if column not in matched_canonical
    ]
    # An extra column is one the report does not know under any spelling.
    extra_columns = [
        column
        for column in uploaded_columns
        if normalize_column_name(column) not in lookup
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
