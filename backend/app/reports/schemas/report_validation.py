from pydantic import BaseModel, Field


class ReportValidationResult(BaseModel):
    valid: bool
    missing_columns: list[str]
    extra_columns: list[str]
    validation_score: int = Field(ge=0, le=100)
    # Which sheet of the workbook this result is for (None for a CSV).
    sheet_name: str | None = None

