import re
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

SECONDS_PER_DAY = 24 * 60 * 60

# pandas writes timedeltas as ISO 8601 durations, e.g. "P0DT8H30M0S".
ISO_DURATION_PATTERN = re.compile(
    r"^P(?:(?P<days>\d+)D)?T?(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?"
    r"(?:(?P<seconds>\d+(?:\.\d+)?)S)?$"
)


def clean_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip()
    return value


def is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


# A cell that says NA / N/A is real text in a text column (a TL called "NA", a
# client called "N/A"). In a number, time, date or yes/no column it can only mean
# "no value", so those parsers treat it as blank. See null_if_na().
NA_TEXT = {"na", "n/a", "nan", "null", "none"}


def null_if_na(value: Any) -> Any:
    """NA-like text -> None, anything else unchanged. For non-text columns only."""
    if isinstance(value, str) and value.strip().lower() in NA_TEXT:
        return None
    return value


def normalize_column(column_name: str) -> str:
    return " ".join(str(column_name).strip().lower().replace("_", " ").split())


def get_raw_value(raw_data: dict[str, Any], column_name: str) -> Any:
    if column_name in raw_data:
        return clean_value(raw_data[column_name])

    normalized_target = normalize_column(column_name)
    for key, value in raw_data.items():
        if normalize_column(key) == normalized_target:
            return clean_value(value)

    return None


def require_raw_value(raw_data: dict[str, Any], column_name: str) -> Any:
    value = get_raw_value(raw_data=raw_data, column_name=column_name)
    if is_blank(value):
        raise ValueError(f"Missing required column value: {column_name}")
    return value


def time_to_seconds(value: Any) -> int:
    value = null_if_na(clean_value(value))
    if is_blank(value):
        raise ValueError("Time value is required")
    if isinstance(value, timedelta):
        return int(value.total_seconds())
    if isinstance(value, (int, float, Decimal)):
        numeric_value = float(value)
        # Excel stores durations as a fraction of a day (0.5 == 12:00:00).
        if 0 < numeric_value < 1:
            return int(round(numeric_value * SECONDS_PER_DAY))
        return int(numeric_value)

    text_value = str(value).strip()
    iso_match = ISO_DURATION_PATTERN.match(text_value)
    if iso_match and text_value not in {"P", "PT"}:
        days, hours, minutes, seconds = (
            float(iso_match.group(group) or 0)
            for group in ("days", "hours", "minutes", "seconds")
        )
        return int((days * SECONDS_PER_DAY) + (hours * 3600) + (minutes * 60) + seconds)

    parts = text_value.split(":")
    if len(parts) != 3:
        raise ValueError(f"Invalid time value: {value}")

    try:
        hours, minutes, seconds = [int(float(part)) for part in parts]
    except ValueError as exc:
        raise ValueError(f"Invalid time value: {value}") from exc

    if minutes < 0 or minutes > 59 or seconds < 0 or seconds > 59:
        raise ValueError(f"Invalid time value: {value}")

    return (hours * 3600) + (minutes * 60) + seconds


def duration_to_minutes(value: Any) -> int:
    value = null_if_na(clean_value(value))
    if is_blank(value):
        return 0
    if isinstance(value, str) and (":" in value or value.strip().upper().startswith("P")):
        return time_to_seconds(value) // 60
    return parse_int(value)


def parse_time(value: Any) -> time:
    value = null_if_na(clean_value(value))
    if isinstance(value, datetime):
        return value.time()
    if isinstance(value, time):
        return value
    if isinstance(value, (int, float, Decimal)):
        numeric_value = float(value)
        if 0 <= numeric_value < 1:
            total_seconds = int(round(numeric_value * 24 * 60 * 60))
        else:
            total_seconds = int(numeric_value)
        total_seconds = total_seconds % (24 * 60 * 60)
        return (datetime.min + timedelta(seconds=total_seconds)).time()
    if is_blank(value):
        raise ValueError("Time value is required")

    time_text = str(value).strip()
    for time_format in (
        "%H:%M:%S",
        "%H:%M",
        "%I:%M:%S %p",
        "%I:%M %p",
    ):
        try:
            return datetime.strptime(time_text, time_format).time()
        except ValueError:
            continue

    raise ValueError(f"Invalid time value: {value}")


def parse_bool(
    value: Any,
    *,
    default: bool = False,
    true_values: set[str] | None = None,
    false_values: set[str] | None = None,
) -> bool:
    value = null_if_na(clean_value(value))
    if is_blank(value):
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float, Decimal)):
        return bool(value)

    normalized = str(value).strip().lower()
    truthy_values = true_values or {"1", "true", "yes", "y", "adherence", "adhered"}
    falsy_values = false_values or {
        "0",
        "false",
        "no",
        "n",
        "non adherence",
        "not adhered",
    }
    if normalized in truthy_values:
        return True
    if normalized in falsy_values:
        return False

    raise ValueError(f"Invalid boolean value: {value}")


def parse_int(value: Any, *, default: int = 0) -> int:
    value = null_if_na(clean_value(value))
    if is_blank(value):
        return default
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float, Decimal)):
        return int(value)

    normalized = str(value).replace(",", "").strip()
    return int(float(normalized))


def parse_decimal(value: Any, *, default: Decimal = Decimal("0")) -> Decimal:
    value = null_if_na(clean_value(value))
    if is_blank(value):
        return default

    normalized = str(value).replace("%", "").replace(",", "").strip()
    try:
        return Decimal(normalized)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid numeric value: {value}") from exc


def parse_percent(value: Any, *, default: Decimal = Decimal("0")) -> Decimal:
    """Parse a percentage column into percent points (87.5 means 87.5%).

    - Text with a % sign ("87.5%") is taken as written.
    - Excel percent cells reach us as fractions (0.875 for 87.5%), so a plain
      number above 0 and up to 1 is scaled by 100.
    - Any other number (e.g. 87.5) is taken as already being in percent points.

    Limitation: a genuine plain-number value of 1 or less (such as 0.5 meaning
    0.5%) cannot be told apart from an Excel fraction and will be scaled up.
    """
    value = null_if_na(clean_value(value))
    if is_blank(value):
        return default

    number = parse_decimal(value)
    has_percent_sign = isinstance(value, str) and "%" in value
    if not has_percent_sign and Decimal("0") < number <= Decimal("1"):
        return number * 100
    return number


def parse_date(value: Any) -> date:
    value = null_if_na(clean_value(value))
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)):
        return (datetime(1899, 12, 30) + timedelta(days=float(value))).date()
    if is_blank(value):
        raise ValueError("Date value is required")

    date_text = str(value).strip()
    normalized = date_text.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized).date()
    except ValueError:
        pass

    for date_format in (
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%m-%d-%Y",
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d-%b-%Y",
        "%d %b %Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y %H:%M",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M",
        "%Y-%m-%d %I:%M:%S %p",
        "%d-%m-%Y %I:%M:%S %p",
        "%d/%m/%Y %I:%M:%S %p",
        "%m/%d/%Y %I:%M:%S %p",
    ):
        try:
            return datetime.strptime(date_text, date_format).date()
        except ValueError:
            continue

    raise ValueError(f"Invalid date value: {value}")
