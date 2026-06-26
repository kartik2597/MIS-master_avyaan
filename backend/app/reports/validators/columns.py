from collections.abc import Iterable

from app.reports.registry import get_report_definition
from app.reports.report_types import ReportType
from app.reports.schemas import ColumnValidationResult


def normalize_column_name(column_name: str) -> str:
    return " ".join(column_name.strip().lower().split())


def validate_columns(
    report_type: ReportType | str,
    uploaded_columns: Iterable[str],
) -> ColumnValidationResult:
    report_definition = get_report_definition(report_type)
    normalized_uploaded_columns = {
        normalize_column_name(column) for column in uploaded_columns
    }

    missing_columns = [
        column
        for column in report_definition.required_columns
        if normalize_column_name(column) not in normalized_uploaded_columns
    ]

    return ColumnValidationResult(
        valid=not missing_columns,
        missing_columns=missing_columns,
    )

