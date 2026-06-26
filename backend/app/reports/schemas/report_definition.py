from pydantic import BaseModel, Field

from app.reports.report_types import ReportType


class ReportDefinition(BaseModel):
    report_type: ReportType
    required_columns: list[str] = Field(default_factory=list)
    optional_columns: list[str] = Field(default_factory=list)
    description: str


class ColumnValidationResult(BaseModel):
    valid: bool
    missing_columns: list[str]

