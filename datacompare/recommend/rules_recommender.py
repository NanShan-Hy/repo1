"""Simple heuristics for suggesting comparison rules."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional

import numpy as np
import pandas as pd


@dataclass
class RuleSuggestion:
    zero_equals_null: bool
    numeric_tolerance: float
    candidate_columns: List[str]
    notes: List[str]


def suggest_rules(
    left_df: pd.DataFrame,
    right_df: pd.DataFrame,
    *,
    numeric_columns: Optional[Iterable[str]] = None,
) -> RuleSuggestion:
    """Suggest comparison rules such as numeric tolerance."""

    numeric_columns = list(numeric_columns) if numeric_columns else []
    if not numeric_columns:
        numeric_columns = [
            col
            for df in (left_df, right_df)
            for col in df.columns
            if pd.api.types.is_numeric_dtype(df[col])
        ]

    zeros_present = False
    for df in (left_df, right_df):
        for col in df.columns:
            series = df[col]
            if (series == 0).any() and series.isna().any():
                zeros_present = True
                break
        if zeros_present:
            break

    tolerance_samples: List[float] = []
    for df in (left_df, right_df):
        for col in numeric_columns:
            if col not in df:
                continue
            series = pd.to_numeric(df[col], errors="coerce")
            series = series.dropna()
            if len(series) < 10:
                continue
            std = float(series.std())
            if not np.isfinite(std) or std == 0:
                continue
            tolerance_samples.append(std * 0.05)

    numeric_tolerance = float(np.median(tolerance_samples)) if tolerance_samples else 0.0
    notes: List[str] = []
    if zeros_present:
        notes.append("Detected columns containing both 0 and null values; consider enabling 0=空 equivalence.")
    if numeric_tolerance > 0:
        notes.append(
            "Suggested numeric tolerance is derived from 5% of the standard deviation across numeric columns."
        )

    return RuleSuggestion(
        zero_equals_null=zeros_present,
        numeric_tolerance=round(numeric_tolerance, 6),
        candidate_columns=sorted(set(numeric_columns)),
        notes=notes,
    )


__all__ = ["RuleSuggestion", "suggest_rules"]
