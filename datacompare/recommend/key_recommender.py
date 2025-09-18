"""Join key recommendation heuristics."""
from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import List, Sequence

import pandas as pd


@dataclass
class KeyCandidate:
    columns: Sequence[str]
    uniqueness: float
    null_ratio: float
    score: float

    def as_dict(self) -> dict:
        return {
            "columns": list(self.columns),
            "uniqueness": self.uniqueness,
            "null_ratio": self.null_ratio,
            "score": self.score,
        }


def _compute_uniqueness(df: pd.DataFrame, columns: Sequence[str]) -> float:
    if df.empty:
        return 0.0
    unique_rows = df[list(columns)].drop_duplicates()
    return len(unique_rows) / len(df)


def _compute_null_ratio(df: pd.DataFrame, columns: Sequence[str]) -> float:
    if df.empty:
        return 0.0
    return df[list(columns)].isna().any(axis=1).mean()


def recommend_join_keys(
    df: pd.DataFrame,
    *,
    top_n: int = 5,
    max_combination_size: int = 2,
) -> List[KeyCandidate]:
    """Return top-N join key candidates based on uniqueness heuristics."""

    numeric_columns = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    object_columns = [c for c in df.columns if pd.api.types.is_string_dtype(df[c])]
    candidate_columns = numeric_columns + object_columns
    candidates: List[KeyCandidate] = []

    for size in range(1, max_combination_size + 1):
        for combo in itertools.combinations(candidate_columns, size):
            uniqueness = _compute_uniqueness(df, combo)
            null_ratio = _compute_null_ratio(df, combo)
            penalty = 0.15 * (size - 1)
            score = uniqueness * (1 - null_ratio) - penalty
            if uniqueness < 0.1:
                score -= 0.3
            candidates.append(
                KeyCandidate(columns=combo, uniqueness=uniqueness, null_ratio=null_ratio, score=score)
            )

    candidates.sort(key=lambda item: item.score, reverse=True)
    return candidates[:top_n]


__all__ = ["KeyCandidate", "recommend_join_keys"]
