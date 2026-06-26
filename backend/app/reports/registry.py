from app.reports.report_types import ReportType
from app.reports.schemas import ReportDefinition


REPORT_REGISTRY: dict[ReportType, ReportDefinition] = {
    ReportType.APR: ReportDefinition(
        report_type=ReportType.APR,
        required_columns=[
            "Agent ID",
            "Agent Name",
            "Total Calls",
        ],
        optional_columns=[],
        description="Agent performance report definition.",
    ),
    ReportType.CALL_COUNT: ReportDefinition(
        report_type=ReportType.CALL_COUNT,
        required_columns=[
            "Agent ID",
            "Agent Name",
            "Call Count",
        ],
        optional_columns=[],
        description="Call count report definition.",
    ),
    ReportType.CONVERTER: ReportDefinition(
        report_type=ReportType.CONVERTER,
        required_columns=[
            "Agent ID",
            "Agent Name",
            "Converted Count",
        ],
        optional_columns=[],
        description="Converter report definition.",
    ),
    ReportType.SHIFT_ADHERENCE: ReportDefinition(
        report_type=ReportType.SHIFT_ADHERENCE,
        required_columns=[
            "Agent ID",
            "Agent Name",
            "Shift Date",
            "Adherence %",
        ],
        optional_columns=[],
        description="Shift adherence report definition.",
    ),
    ReportType.SHRINKAGE: ReportDefinition(
        report_type=ReportType.SHRINKAGE,
        required_columns=[
            "Agent ID",
            "Agent Name",
            "Shrinkage %",
        ],
        optional_columns=[],
        description="Shrinkage report definition.",
    ),
    ReportType.SUPPORT_ATTENDANCE: ReportDefinition(
        report_type=ReportType.SUPPORT_ATTENDANCE,
        required_columns=[
            "Agent ID",
            "Agent Name",
            "Attendance Date",
            "Status",
        ],
        optional_columns=[],
        description="Support attendance report definition.",
    ),
    ReportType.SUPPORT_BREAK: ReportDefinition(
        report_type=ReportType.SUPPORT_BREAK,
        required_columns=[
            "Agent ID",
            "Agent Name",
            "Break Start",
            "Break End",
        ],
        optional_columns=[],
        description="Support break report definition.",
    ),
    ReportType.SUPPORT_ADHERENCE: ReportDefinition(
        report_type=ReportType.SUPPORT_ADHERENCE,
        required_columns=[
            "Agent ID",
            "Agent Name",
            "Support Date",
            "Adherence %",
        ],
        optional_columns=[],
        description="Support adherence report definition.",
    ),
    ReportType.MASTER_DATABASE: ReportDefinition(
        report_type=ReportType.MASTER_DATABASE,
        required_columns=[
            "Employee ID",
            "Employee Name",
            "Email",
        ],
        optional_columns=[],
        description="Master database report definition.",
    ),
    ReportType.TRAINING_DATA: ReportDefinition(
        report_type=ReportType.TRAINING_DATA,
        required_columns=[
            "Employee ID",
            "Employee Name",
            "Training Name",
            "Training Date",
        ],
        optional_columns=[],
        description="Training data report definition.",
    ),
}


def get_report_definition(report_type: ReportType | str) -> ReportDefinition:
    normalized_report_type = ReportType(report_type)
    return REPORT_REGISTRY[normalized_report_type]


def get_all_report_types() -> list[ReportType]:
    return list(REPORT_REGISTRY.keys())

