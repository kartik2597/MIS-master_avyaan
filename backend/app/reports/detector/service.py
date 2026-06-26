from collections.abc import Iterable

from pydantic import BaseModel, Field

from app.reports.registry import REPORT_REGISTRY
from app.reports.validators.columns import normalize_column_name


class DetectionResult(BaseModel):
    detected_report_type: str | None
    confidence_score: int = Field(ge=0, le=100)
    matched_columns: list[str]
    missing_columns: list[str]


def detect_report_type(uploaded_columns: list[str]) -> DetectionResult:
    normalized_uploaded_columns = normalize_columns(uploaded_columns)
    best_result: DetectionResult | None = None

    for report_definition in REPORT_REGISTRY.values():
        required_columns = report_definition.required_columns
        total_required_columns = len(required_columns)
        matched_columns = [
            column
            for column in required_columns
            if normalize_column_name(column) in normalized_uploaded_columns
        ]
        missing_columns = [
            column
            for column in required_columns
            if normalize_column_name(column) not in normalized_uploaded_columns
        ]

        confidence_score = calculate_confidence_score(
            matched_required_columns=len(matched_columns),
            total_required_columns=total_required_columns,
        )
        result = DetectionResult(
            detected_report_type=report_definition.report_type.value,
            confidence_score=confidence_score,
            matched_columns=matched_columns,
            missing_columns=missing_columns,
        )

        if is_better_detection(result, best_result):
            best_result = result

    if best_result is None or best_result.confidence_score == 0:
        return DetectionResult(
            detected_report_type=None,
            confidence_score=0,
            matched_columns=[],
            missing_columns=[],
        )

    return best_result


def normalize_columns(columns: Iterable[str]) -> set[str]:
    return {normalize_column_name(column) for column in columns}


def calculate_confidence_score(
    *,
    matched_required_columns: int,
    total_required_columns: int,
) -> int:
    if total_required_columns == 0:
        return 0
    return round((matched_required_columns / total_required_columns) * 100)


def is_better_detection(
    candidate: DetectionResult,
    current_best: DetectionResult | None,
) -> bool:
    if current_best is None:
        return True
    if candidate.confidence_score != current_best.confidence_score:
        return candidate.confidence_score > current_best.confidence_score
    return len(candidate.matched_columns) > len(current_best.matched_columns)

