from pydantic import BaseModel


class ArrangerTableInfo(BaseModel):
    name: str
    rows: int
    columns: int


class ArrangerPreview(BaseModel):
    columns: list[str]
    rows: list[list[str]]
    total_rows: int
    preview_limit: int
    # The column the files were joined on (None with a single file or no common column).
    key: str | None
    # Every column name that all uploaded files share: the choices for `key`.
    common_columns: list[str]
    tables: list[ArrangerTableInfo]
    notes: list[str]
