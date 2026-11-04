from pydantic import BaseModel, Field


class ImportSummary(BaseModel):
    total_records: int = Field(ge=0)
    processed_records: int = Field(ge=0)
    failed_records: int = Field(ge=0)
    # Which rows were skipped and why (first few). None when nothing failed.
    message: str | None = None
