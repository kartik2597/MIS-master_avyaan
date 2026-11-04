from collections.abc import Iterable

from app.reports.headers import map_uploaded_columns, normalize_column_name
from app.reports.registry import get_header_lookup, get_report_definition
from app.reports.report_types import ReportType
from app.reports.schemas import ColumnValidationResult

__all__ = ["normalize_column_name", "validate_columns"]


def validate_columns(
    report_type: ReportType | str,
    uploaded_columns: Iterable[str],
) -> ColumnValidationResult:
    report_definition = get_report_definition(report_type)
    matched_canonical = set(
        map_uploaded_columns(uploaded_columns, get_header_lookup(report_type)).values()
    )

    missing_columns = [
        column
        for column in report_definition.required_columns
        if column not in matched_canonical
    ]

    return ColumnValidationResult(
        valid=not missing_columns,
        missing_columns=missing_columns,
    )
