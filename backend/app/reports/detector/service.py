from collections.abc import Iterable

from pydantic import BaseModel, Field

from app.reports.headers import map_uploaded_columns, normalize_column_name
from app.reports.registry import REPORT_REGISTRY, get_header_lookup


# A file is only given a report type when it matches enough of that type's required
# columns. Without this, the small types (3-4 required columns, e.g. CALL_COUNT or
# TRAINING_DATA) could claim any file that happened to share an "Agent ID" or
# "Employee Name" column. A file below the bar is left as UNKNOWN, so the person
# sees that it was not recognised instead of a misleading list of missing columns.
MIN_DETECTION_CONFIDENCE = 70
MIN_MATCHED_COLUMNS = 3


class DetectionResult(BaseModel):
    detected_report_type: str | None
    confidence_score: int = Field(ge=0, le=100)
    matched_columns: list[str]
    missing_columns: list[str]


def detect_report_type(uploaded_columns: list[str]) -> DetectionResult:
    best_result: DetectionResult | None = None

    for report_type, report_definition in REPORT_REGISTRY.items():
        required_columns = report_definition.required_columns
        total_required_columns = len(required_columns)
        # Match by canonical name so aliases and spelling variants all count.
        matched_canonical = set(
            map_uploaded_columns(
                uploaded_columns, get_header_lookup(report_type)
            ).values()
        )
        matched_columns = [
            column for column in required_columns if column in matched_canonical
        ]
        missing_columns = [
            column for column in required_columns if column not in matched_canonical
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

    if (
        best_result is None
        or best_result.confidence_score < MIN_DETECTION_CONFIDENCE
        or len(best_result.matched_columns) < MIN_MATCHED_COLUMNS
    ):
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
