"""Flexible column-header matching shared by report detection and validation.

Real MIS files name the same column in many ways ("Emp ID", "Employee_ID",
"employee id"). This module turns every header into one normal form and maps
known alternative names (aliases) onto the column name the system expects.

This module imports nothing from the rest of the app so any module can use it.
"""

import re
from collections.abc import Iterable, Mapping, Sequence

_SEPARATORS = re.compile(r"[\s_\-.]+")


def normalize_column_name(column_name: object) -> str:
    """Lower-case a header and treat spaces, underscores, hyphens and dots alike.

    "Employee_ID", "employee-id", "Employee  ID" and " employee id " all become
    "employee id".
    """
    text = str(column_name).replace("\ufeff", "").strip().lower()
    return _SEPARATORS.sub(" ", text).strip()


def build_header_lookup(
    required_columns: Sequence[str],
    optional_columns: Sequence[str],
    column_aliases: Mapping[str, Sequence[str]],
) -> dict[str, str]:
    """Map every accepted spelling (normalized) to the canonical column name.

    The canonical names always win over aliases, and the first spelling listed
    wins when two names normalize to the same text.
    """
    lookup: dict[str, str] = {}
    for canonical in [*required_columns, *optional_columns]:
        lookup.setdefault(normalize_column_name(canonical), canonical)
    for canonical, aliases in column_aliases.items():
        for alias in aliases:
            lookup.setdefault(normalize_column_name(alias), canonical)
    return lookup


def map_uploaded_columns(
    uploaded_columns: Iterable[object],
    lookup: Mapping[str, str],
) -> dict[str, str]:
    """Return {uploaded column name: canonical column name} for known columns.

    If a file has two columns that mean the same thing, the first one is used
    and the second is left out of the mapping (it is treated as an extra column).
    """
    mapping: dict[str, str] = {}
    used_canonical: set[str] = set()
    for uploaded in uploaded_columns:
        uploaded_name = str(uploaded)
        canonical = lookup.get(normalize_column_name(uploaded_name))
        if canonical is None or canonical in used_canonical:
            continue
        mapping[uploaded_name] = canonical
        used_canonical.add(canonical)
    return mapping
