"""Duplicate detection utilities."""
from __future__ import annotations

import itertools
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import List, Optional, Sequence

import numpy as np
import pandas as pd


@dataclass
class ExactDuplicateResult:
    unique: pd.DataFrame
    duplicates: pd.DataFrame
    groups: pd.DataFrame


@dataclass
class ApproximateDuplicateResult:
    pairs: pd.DataFrame
    threshold: float


@dataclass
class DeduplicationResult:
    exact: ExactDuplicateResult
    approximate: Optional[ApproximateDuplicateResult] = None

    def summary(self) -> dict:
        return {
            "exact_duplicates": int(len(self.exact.duplicates)),
            "approximate_pairs": int(len(self.approximate.pairs)) if self.approximate else 0,
        }


def find_exact_duplicates(df: pd.DataFrame, subset: Optional[Sequence[str]] = None) -> ExactDuplicateResult:
    subset = list(subset) if subset else list(df.columns)
    duplicated_mask = df.duplicated(subset=subset, keep="first")
    duplicate_rows = df[duplicated_mask].copy()
    unique_rows = df.drop_duplicates(subset=subset, keep="first").copy()

    key_series = df[subset].astype(str).agg("|".join, axis=1)
    group_mask = key_series.duplicated(keep=False)
    groups = df[group_mask].copy()
    group_ids = pd.factorize(key_series[group_mask])[0]
    groups.insert(0, "dedup_group_id", group_ids)
    groups["is_primary"] = ~groups.duplicated(subset=subset, keep="first")

    return ExactDuplicateResult(unique=unique_rows, duplicates=duplicate_rows, groups=groups)


def _normalise_text(value: object) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    return str(value).strip().lower()


def _text_signature(row: pd.Series, columns: Sequence[str]) -> str:
    if not columns:
        columns = list(row.index)
    return " ".join(_normalise_text(row[col]) for col in columns if col in row)


def _text_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _numeric_similarity(row_a: pd.Series, row_b: pd.Series, columns: Sequence[str]) -> float:
    if not columns:
        return 0.0
    scores: List[float] = []
    for column in columns:
        if column not in row_a or column not in row_b:
            continue
        try:
            a = float(row_a[column])
            b = float(row_b[column])
        except (TypeError, ValueError):
            continue
        if not np.isfinite(a) or not np.isfinite(b):
            continue
        denom = max(abs(a), abs(b), 1.0)
        score = 1.0 - min(1.0, abs(a - b) / denom)
        scores.append(score)
    return float(np.mean(scores)) if scores else 0.0


def find_approximate_duplicates(
    df: pd.DataFrame,
    *,
    text_columns: Optional[Sequence[str]] = None,
    numeric_columns: Optional[Sequence[str]] = None,
    threshold: float = 0.85,
) -> ApproximateDuplicateResult:
    if df.empty:
        return ApproximateDuplicateResult(pairs=pd.DataFrame(columns=["group_id", "primary_index", "candidate_index", "score"]), threshold=threshold)

    text_columns = list(text_columns) if text_columns else []
    numeric_columns = list(numeric_columns) if numeric_columns else []

    signatures = df.apply(lambda row: _text_signature(row, text_columns), axis=1)
    buckets = {}
    for idx, signature in signatures.items():
        bucket_key = signature[:1] if signature else "__"
        buckets.setdefault(bucket_key, []).append((idx, signature))

    records: List[dict] = []
    for bucket in buckets.values():
        if len(bucket) < 2:
            continue
        for (idx_a, sig_a), (idx_b, sig_b) in itertools.combinations(bucket, 2):
            text_score = _text_similarity(sig_a, sig_b)
            if text_score < threshold:
                continue
            row_a = df.loc[idx_a]
            row_b = df.loc[idx_b]
            numeric_score = _numeric_similarity(row_a, row_b, numeric_columns)
            combined = 0.7 * text_score + 0.3 * numeric_score
            if combined >= threshold:
                records.append(
                    {
                        "group_id": int(idx_a),
                        "primary_index": int(idx_a),
                        "candidate_index": int(idx_b),
                        "score": round(combined, 4),
                    }
                )

    pairs_df = pd.DataFrame(records, columns=["group_id", "primary_index", "candidate_index", "score"])
    return ApproximateDuplicateResult(pairs=pairs_df, threshold=threshold)


def deduplicate(
    df: pd.DataFrame,
    *,
    subset: Optional[Sequence[str]] = None,
    text_columns: Optional[Sequence[str]] = None,
    numeric_columns: Optional[Sequence[str]] = None,
    threshold: float = 0.85,
) -> DeduplicationResult:
    exact = find_exact_duplicates(df, subset=subset)
    approximate = find_approximate_duplicates(
        df,
        text_columns=text_columns,
        numeric_columns=numeric_columns,
        threshold=threshold,
    )
    return DeduplicationResult(exact=exact, approximate=approximate)


__all__ = [
    "ExactDuplicateResult",
    "ApproximateDuplicateResult",
    "DeduplicationResult",
    "find_exact_duplicates",
    "find_approximate_duplicates",
    "deduplicate",
]
