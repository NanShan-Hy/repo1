"""Type inference helpers used by the normalization layer."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List

import pandas as pd

_TIMEPERIOD_PATTERN = re.compile(r"^(?:[01]?\d|2[0-4]):[0-5]\d$")
_BOOL_ALIASES = {"true", "false", "yes", "no", "y", "n", "t", "f", "是", "否"}


@dataclass
class InferredType:
    column: str
    logical_type: str
    confidence: float


@dataclass
class TypeInferenceResult:
    columns: List[InferredType]

    def as_mapping(self) -> Dict[str, str]:
        return {item.column: item.logical_type for item in self.columns}


def _infer_boolean(series: pd.Series) -> float:
    normalized = series.dropna().astype(str).str.lower().str.strip()
    if normalized.empty:
        return 0.0
    matches = normalized.isin(_BOOL_ALIASES | {"1", "0"})
    return matches.mean()


def _infer_numeric(series: pd.Series) -> float:
    coerced = pd.to_numeric(series.dropna(), errors="coerce")
    return coerced.notna().mean() if not coerced.empty else 0.0


def _infer_datetime(series: pd.Series) -> float:
    coerced = pd.to_datetime(series.dropna(), errors="coerce", utc=False, format=None)
    return coerced.notna().mean() if not coerced.empty else 0.0


def _infer_timeperiod(series: pd.Series) -> float:
    normalized = series.dropna().astype(str).str.strip()
    if normalized.empty:
        return 0.0
    return normalized.str.match(_TIMEPERIOD_PATTERN).mean()


def _infer_enum(series: pd.Series) -> float:
    series = series.dropna()
    if series.empty:
        return 0.0
    unique_ratio = series.nunique(dropna=True) / len(series)
    return 1.0 - unique_ratio


def infer_column_types(df: pd.DataFrame) -> TypeInferenceResult:
    """Infer logical column types with simple heuristics.

    The goal is to give the recommendation engine actionable hints without
    incurring heavy computation.  Each column is scored against boolean,
    numeric, datetime, and time-period heuristics; the highest confidence wins.
    Columns with no strong signal default to ``"string"``.
    """

    results: List[InferredType] = []
    for column in df.columns:
        series = df[column]
        scores = {
            "boolean": _infer_boolean(series),
            "numeric": _infer_numeric(series),
            "datetime": _infer_datetime(series),
            "timeperiod": _infer_timeperiod(series),
            "enum": _infer_enum(series),
        }
        logical_type = max(scores, key=scores.get)
        confidence = scores[logical_type]
        if logical_type == "enum" and confidence < 0.5:
            logical_type = "string"
        elif confidence < 0.4:
            logical_type = "string"
            confidence = 0.4 if scores.get("numeric", 0) > 0 else 0.2
        results.append(InferredType(column=column, logical_type=logical_type, confidence=confidence))
    return TypeInferenceResult(columns=results)


__all__ = ["InferredType", "TypeInferenceResult", "infer_column_types"]
