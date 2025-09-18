"""Column standardisation utilities.

The module implements the column name cleansing heuristics described in the
requirements: trimming whitespace, unifying case, handling full-width
characters, and providing a reversible mapping between the original and
standardised labels.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, MutableMapping

import pandas as pd

def _to_half_width(text: str) -> str:
    buffer = []
    for char in text:
        code = ord(char)
        # Full-width space
        if code == 0x3000:
            buffer.append(" ")
            continue
        # General full-width alphanumerics
        if 0xFF01 <= code <= 0xFF5E:
            buffer.append(chr(code - 0xFEE0))
        else:
            buffer.append(char)
    return "".join(buffer)


def _slugify(text: str) -> str:
    text = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "_", text)
    text = re.sub(r"_+", "_", text)
    return text.strip("_")


@dataclass
class ColumnNormalizationResult:
    data: pd.DataFrame
    mapping: Dict[str, str]
    collisions: Dict[str, List[str]]

    def reverse_mapping(self) -> Dict[str, str]:
        return {v: k for k, v in self.mapping.items()}


def normalise_column_names(
    df: pd.DataFrame,
    *,
    case: str = "lower",
    deduplicate: bool = True,
) -> ColumnNormalizationResult:
    """Return a copy of ``df`` with cleaned column names.

    Parameters
    ----------
    case:
        Either ``"lower"`` or ``"upper"`` to standardise casing.  When ``None``
        the original casing is preserved after other cleaning rules.
    deduplicate:
        When ``True`` conflicting standard names receive numeric suffixes to
        guarantee uniqueness.  All collisions are tracked in the result.
    """

    if case not in {"lower", "upper", None}:
        raise ValueError("case must be 'lower', 'upper' or None")

    mapping: MutableMapping[str, str] = {}
    collisions: MutableMapping[str, List[str]] = {}
    seen: MutableMapping[str, int] = {}

    cleaned_columns: List[str] = []
    for original in df.columns:
        standard = _to_half_width(str(original)).strip()
        standard = standard.replace("\xa0", " ")  # non-breaking space
        standard = _slugify(standard)
        if case == "lower":
            standard = standard.lower()
        elif case == "upper":
            standard = standard.upper()

        if not standard:
            standard = "column"

        if deduplicate:
            base = standard
            count = seen.get(base, 0)
            if count:
                standard = f"{base}_{count+1}"
                collisions.setdefault(base, []).append(str(original))
            seen[base] = count + 1
        mapping[str(original)] = standard
        cleaned_columns.append(standard)

    renamed = df.copy()
    renamed.columns = cleaned_columns
    return ColumnNormalizationResult(data=renamed, mapping=dict(mapping), collisions=dict(collisions))


__all__ = ["ColumnNormalizationResult", "normalise_column_names"]
