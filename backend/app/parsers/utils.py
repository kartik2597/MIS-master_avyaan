from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any


def clean_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip()
    return value


def is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


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
    value = clean_value(value)
    if is_blank(value):
        raise ValueError("Time value is required")
    if isinstance(value, timedelta):
        return int(value.total_seconds())
    if isinstance(value, (int, float, Decimal)):
        return int(value)

    parts = str(value).split(":")
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
    value = clean_value(value)
    if is_blank(value):
        return 0
    if isinstance(value, str) and ":" in value:
        return time_to_seconds(value) // 60
    return parse_int(value)


def parse_time(value: Any) -> time:
    value = clean_value(value)
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
    value = clean_value(value)
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
    value = clean_value(value)
    if is_blank(value):
        return default
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float, Decimal)):
        return int(value)

    normalized = str(value).replace(",", "").strip()
    return int(float(normalized))


def parse_decimal(value: Any, *, default: Decimal = Decimal("0")) -> Decimal:
    value = clean_value(value)
    if is_blank(value):
        return default

    normalized = str(value).replace("%", "").replace(",", "").strip()
    try:
        return Decimal(normalized)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid numeric value: {value}") from exc


def parse_date(value: Any) -> date:
    value = clean_value(value)
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
