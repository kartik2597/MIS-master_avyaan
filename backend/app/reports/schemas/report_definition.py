from pydantic import BaseModel, Field

from app.reports.report_types import ReportType


class ReportDefinition(BaseModel):
    report_type: ReportType
    required_columns: list[str] = Field(default_factory=list)
    optional_columns: list[str] = Field(default_factory=list)
    # canonical column name -> other names the same column is known by
    column_aliases: dict[str, list[str]] = Field(default_factory=dict)
    description: str


class ColumnValidationResult(BaseModel):
    valid: bool
    missing_columns: list[str]
