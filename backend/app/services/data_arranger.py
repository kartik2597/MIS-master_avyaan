"""Arrange messy spreadsheets, join several of them on a common column, and export.

Nothing here touches the database. The files are read, tidied, joined in memory and
handed back, so it can be used for any sheet, not only the four MIS report types.

Every cell is kept as text. That is on purpose: employee IDs such as "00123" must not
turn into the number 123 on the way through.
"""

import csv
import math
import re
from dataclasses import dataclass, field
from io import BytesIO, StringIO
from pathlib import PurePath

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter


JOIN_TYPES = ("outer", "left", "inner")
EXPORT_FORMATS = ("xlsx", "csv")
CSV_SUFFIXES = {".csv", ".tsv", ".txt"}
EXCEL_SUFFIXES = {".xlsx", ".xlsm", ".xls"}
SUPPORTED_SUFFIXES = CSV_SUFFIXES | EXCEL_SUFFIXES

# Reports often start with a title or a blank row. The header is the first row, within
# this many rows, that is mostly filled in.
HEADER_SCAN_ROWS = 20
PREVIEW_ROWS = 200


class ArrangerError(ValueError):
    """A problem the user can fix (bad file, unknown column). Shown as a 400."""


@dataclass
class ArrangeOptions:
    trim: bool = True
    tidy_headers: bool = True
    drop_empty: bool = True
    drop_duplicates: bool = True
    title_case: bool = False


@dataclass
class Table:
    name: str
    frame: pd.DataFrame


@dataclass
class ArrangeResult:
    frame: pd.DataFrame
    key: str | None
    common_columns: list[str]
    tables: list[tuple[str, int, int]]  # name, rows, columns (after arranging)
    notes: list[str] = field(default_factory=list)


# --- Reading ---------------------------------------------------------------------


def _cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    text = str(value)
    # Excel dates come through as "2026-01-31 00:00:00".
    return re.sub(r" 00:00:00$", "", text)


def _unique_headers(headers: list[str], tidy: bool) -> list[str]:
    """Fill blank headers and make duplicates unique; optionally tidy the spacing."""
    result: list[str] = []
    seen: set[str] = set()
    for position, header in enumerate(headers, start=1):
        name = _cell(header)
        if tidy:
            name = re.sub(r"\s+", " ", name).strip()
        if not name.strip():
            name = f"Column {position}"
        candidate, count = name, 1
        while candidate.lower() in seen:
            count += 1
            candidate = f"{name} ({count})"
        seen.add(candidate.lower())
        result.append(candidate)
    return result


def _promote_header(raw: list[list[object]]) -> pd.DataFrame:
    rows = [[_cell(value) for value in row] for row in raw]
    width = max((len(row) for row in rows), default=0)
    if width == 0:
        return pd.DataFrame()
    rows = [row + [""] * (width - len(row)) for row in rows]

    filled = [sum(1 for value in row if value.strip()) for row in rows[:HEADER_SCAN_ROWS]]
    best = max(filled, default=0)
    if best == 0:
        return pd.DataFrame()
    threshold = max(1, math.ceil(best * 0.6))
    header_index = next(i for i, count in enumerate(filled) if count >= threshold)

    headers = _unique_headers(rows[header_index], tidy=False)
    return pd.DataFrame(rows[header_index + 1 :], columns=headers, dtype=str)


def _read_csv(data: bytes) -> list[list[str]]:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("cp1252", errors="replace")
    try:
        delimiter = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|").delimiter
    except csv.Error:
        delimiter = ","
    return list(csv.reader(StringIO(text), delimiter=delimiter))


def load_tables(files: list[tuple[str, bytes]]) -> list[Table]:
    """One Table per CSV file and per non-empty sheet of an Excel file."""
    tables: list[Table] = []
    used: set[str] = set()

    for file_name, data in files:
        path = PurePath(file_name)
        suffix = path.suffix.lower()
        if suffix not in SUPPORTED_SUFFIXES:
            raise ArrangerError(f"{file_name}: unsupported file type. Use XLSX, XLS or CSV.")

        if suffix in CSV_SUFFIXES:
            sheets: dict[str, list[list[object]]] = {"": _read_csv(data)}  # type: ignore[dict-item]
        else:
            try:
                workbook = pd.read_excel(
                    BytesIO(data), sheet_name=None, header=None, dtype=str, keep_default_na=False
                )
            except Exception as exc:  # corrupt file, wrong password, bad extension...
                raise ArrangerError(f"{file_name}: could not be read ({exc}).") from exc
            sheets = {str(name): frame.values.tolist() for name, frame in workbook.items()}

        for sheet_name, raw in sheets.items():
            frame = _promote_header(raw)
            if frame.empty and len(frame.columns) == 0:
                continue
            label = path.stem if len(sheets) == 1 else f"{path.stem} / {sheet_name}"
            base, count = label, 1
            while label in used:
                count += 1
                label = f"{base} ({count})"
            used.add(label)
            tables.append(Table(label, frame))

    if not tables:
        raise ArrangerError("No data was found in the uploaded files.")
    return tables


# --- Arranging -------------------------------------------------------------------


def arrange(frame: pd.DataFrame, options: ArrangeOptions) -> pd.DataFrame:
    df = frame.copy()
    df.columns = _unique_headers(list(df.columns), options.tidy_headers)

    if options.trim:
        df = df.apply(lambda column: column.str.replace(r"\s+", " ", regex=True).str.strip())
    if options.title_case:
        # Only plain words (names, cities). IDs, e-mails and mixed values are left alone.
        def title(column: pd.Series) -> pd.Series:
            is_words = column.str.fullmatch(r"[A-Za-z][A-Za-z .'\-]*")
            return column.where(~is_words, column.str.title())

        df = df.apply(title)
    if options.drop_empty:
        df = df[(df != "").any(axis=1)]
        df = df.loc[:, (df != "").any(axis=0)]
    if options.drop_duplicates:
        df = df.drop_duplicates()
    return df.reset_index(drop=True)


# --- Joining ---------------------------------------------------------------------


def _normalize(name: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(name).lower()).strip()


def find_common_columns(frames: list[pd.DataFrame]) -> list[str]:
    """Column names (compared ignoring case, spaces and punctuation) present in every frame."""
    if len(frames) < 2:
        return []
    others = [{_normalize(column) for column in frame.columns} for frame in frames[1:]]
    return [
        column
        for column in frames[0].columns
        if _normalize(column) and all(_normalize(column) in names for names in others)
    ]


def _find_column(frame: pd.DataFrame, key: str) -> str:
    wanted = _normalize(key)
    for column in frame.columns:
        if _normalize(column) == wanted:
            return column
    raise ArrangerError(f"Column '{key}' was not found in every file.")


def _is_placeholder(value: str) -> bool:
    return value.startswith("\0")


def _key_series(series: pd.Series, tag: str) -> pd.Series:
    """Match key: case, spacing and a trailing ".0" (Excel numbers) are ignored.

    A blank key must never match another blank key, so each gets its own placeholder.
    """
    key = (
        series.str.lower()
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
    )
    placeholders = pd.Series([f"\0{tag}{n}" for n in range(len(key))], index=key.index)
    return key.where(key != "", placeholders)


def _repeats(keys: pd.Series) -> int:
    real = keys[~keys.map(_is_placeholder)]
    return int(real.duplicated().sum())


def merge_tables(
    frames: list[pd.DataFrame], names: list[str], key: str, how: str
) -> tuple[pd.DataFrame, list[str]]:
    notes: list[str] = []
    result = frames[0].copy()
    left_key_column = _find_column(result, key)
    result["__key__"] = _key_series(result[left_key_column], "L")

    if _repeats(result["__key__"]):
        notes.append(
            f"'{names[0]}' has repeated values in '{left_key_column}', so its rows can repeat in the result."
        )

    for position, (frame, name) in enumerate(zip(frames[1:], names[1:]), start=2):
        right = frame.copy()
        right_key_column = _find_column(right, key)
        right["__key__"] = _key_series(right[right_key_column], f"R{position}")

        left_keys = set(result["__key__"])
        right_keys = set(right["__key__"])
        unmatched_left = sum(
            1 for k in result["__key__"] if not _is_placeholder(k) and k not in right_keys
        )
        unmatched_right = sum(
            1 for k in right["__key__"] if not _is_placeholder(k) and k not in left_keys
        )
        if unmatched_left or unmatched_right:
            notes.append(
                f"Joining '{name}': {unmatched_left} earlier row(s) and {unmatched_right} row(s) "
                f"of '{name}' had no match on '{left_key_column}'."
            )
        if _repeats(right["__key__"]):
            notes.append(
                f"'{name}' has repeated values in '{right_key_column}', so matching rows are repeated for each match."
            )

        taken = set(result.columns)
        rename: dict[str, str] = {right_key_column: "__rkey__"}
        for column in right.columns:
            if column in ("__key__", right_key_column):
                continue
            new, count = column, 1
            while new in taken:
                count += 1
                new = f"{column} ({position})" if count == 2 else f"{column} ({position}.{count})"
            taken.add(new)
            rename[column] = new
        right = right.rename(columns=rename)

        result = result.merge(right, on="__key__", how=how)
        result[left_key_column] = result[left_key_column].fillna(result["__rkey__"])
        result = result.drop(columns=["__rkey__"])

    result = result.drop(columns=["__key__"]).fillna("")
    return result.reset_index(drop=True), notes


def sort_frame(frame: pd.DataFrame, column: str) -> pd.DataFrame:
    if column not in frame.columns:
        raise ArrangerError(f"Cannot sort by '{column}': no such column.")
    filled = frame[column] != ""
    numbers = pd.to_numeric(frame[column].str.replace(",", "", regex=False), errors="coerce")
    is_numeric = bool(filled.any()) and bool(numbers[filled].notna().all())
    sort_key = numbers if is_numeric else frame[column].str.casefold()
    ordered = frame.assign(__blank=~filled, __k=sort_key).sort_values(
        ["__blank", "__k"], kind="stable"
    )
    return ordered.drop(columns=["__blank", "__k"]).reset_index(drop=True)


def process(
    files: list[tuple[str, bytes]],
    options: ArrangeOptions,
    key: str | None = None,
    how: str = "outer",
    sort_by: str | None = None,
) -> ArrangeResult:
    if how not in JOIN_TYPES:
        raise ArrangerError(f"Unknown join type '{how}'. Use one of: {', '.join(JOIN_TYPES)}.")

    tables = load_tables(files)
    frames = [arrange(table.frame, options) for table in tables]
    names = [table.name for table in tables]
    info = [(name, len(frame), len(frame.columns)) for name, frame in zip(names, frames)]

    notes: list[str] = []
    common = find_common_columns(frames)
    used_key: str | None = None

    if len(frames) == 1:
        merged = frames[0]
    else:
        if key:
            if not any(_normalize(c) == _normalize(key) for c in common):
                raise ArrangerError(f"Column '{key}' is not present in every file.")
            used_key = key
        elif common:
            used_key = common[0]
        if used_key is None:
            notes.append(
                "No column name is shared by every file, so they cannot be joined. "
                "Rename a header so it matches in each file, or upload fewer files."
            )
            merged = pd.DataFrame()
        else:
            merged, join_notes = merge_tables(frames, names, used_key, how)
            notes.extend(join_notes)

    if sort_by and not merged.empty:
        merged = sort_frame(merged, sort_by)

    return ArrangeResult(frame=merged, key=used_key, common_columns=common, tables=info, notes=notes)


# --- Exporting -------------------------------------------------------------------

CONTENT_TYPES = {
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "csv": "text/csv; charset=utf-8",
}


def to_xlsx(frame: pd.DataFrame) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Arranged data"
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="1F4E78")

    for column, header in enumerate(frame.columns, start=1):
        cell = sheet.cell(row=1, column=column, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")
    for row_number, row in enumerate(frame.itertuples(index=False), start=2):
        for column, value in enumerate(row, start=1):
            cell = sheet.cell(row=row_number, column=column, value=value)
            if isinstance(value, str) and value.startswith("="):
                cell.data_type = "s"  # keep text that starts with "=" as text, not a formula

    sheet.freeze_panes = "A2"
    for column_cells in sheet.columns:
        longest = max((len(str(c.value)) for c in column_cells if c.value is not None), default=8)
        sheet.column_dimensions[get_column_letter(column_cells[0].column)].width = min(longest + 2, 45)

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def to_csv(frame: pd.DataFrame) -> bytes:
    # utf-8 with a BOM so Excel opens accented names correctly.
    return frame.to_csv(index=False).encode("utf-8-sig")


def render(frame: pd.DataFrame, file_format: str) -> bytes:
    if file_format == "xlsx":
        return to_xlsx(frame)
    if file_format == "csv":
        return to_csv(frame)
    raise ArrangerError(f"Unknown export format '{file_format}'.")
