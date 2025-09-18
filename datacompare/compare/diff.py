"""Diff engine implementing multi-column comparison with tolerance rules."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, List, Optional, Sequence

import numpy as np
import pandas as pd


ColumnSpec = str | Sequence[str]


@dataclass
class ColumnMapping:
    """Mapping between left and right datasets."""

    left: ColumnSpec
    right: ColumnSpec
    alias: Optional[str] = None

    def output_name(self) -> str:
        if self.alias:
            return self.alias
        if isinstance(self.left, str):
            return self.left
        if isinstance(self.right, str):
            return self.right
        if isinstance(self.left, Sequence) and not isinstance(self.left, str):
            return "_".join(str(item) for item in self.left)
        if isinstance(self.right, Sequence) and not isinstance(self.right, str):
            return "_".join(str(item) for item in self.right)
        return "column"


@dataclass
class ComparisonConfig:
    treat_zero_as_null: bool = False
    absolute_tolerance: float = 0.0
    relative_tolerance: float = 0.0
    case_insensitive: bool = False
    strip_whitespace: bool = True
    datetime_tolerance: Optional[pd.Timedelta] = None


@dataclass
class DifferenceRecord:
    keys: dict
    column: str
    left_value: Any
    right_value: Any
    difference: Optional[float]
    difference_pct: Optional[float]


@dataclass
class DiffResult:
    matched: pd.DataFrame
    mismatched: pd.DataFrame
    left_only: pd.DataFrame
    right_only: pd.DataFrame
    details: pd.DataFrame
    config: ComparisonConfig = field(default_factory=ComparisonConfig)
    mappings: List[ColumnMapping] = field(default_factory=list)

    def summary(self) -> dict:
        return {
            "matched": int(len(self.matched)),
            "mismatched": int(len(self.mismatched)),
            "left_only": int(len(self.left_only)),
            "right_only": int(len(self.right_only)),
            "differences": int(len(self.details)),
        }


class ComparisonError(RuntimeError):
    pass


def _ensure_columns(df: pd.DataFrame, columns: Iterable[str], side: str) -> None:
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise ComparisonError(f"Missing columns on {side} dataset: {missing}")


def _materialise_columns(df: pd.DataFrame, columns: ColumnSpec, side: str) -> pd.Series:
    if isinstance(columns, str):
        _ensure_columns(df, [columns], side)
        return df[columns]
    cols = list(columns)
    _ensure_columns(df, cols, side)
    concatenated = df[cols].astype(str).fillna("").agg("|".join, axis=1)
    return concatenated


def _normalise_value(value: Any, config: ComparisonConfig) -> Any:
    if value is None:
        return np.nan
    if pd.isna(value):
        return np.nan
    if isinstance(value, str):
        if config.strip_whitespace:
            value = value.strip()
        if config.case_insensitive:
            value = value.lower()
        if value == "":
            return np.nan
        if config.treat_zero_as_null and value in {"0", "0.0", "0.00"}:
            return np.nan
        return value
    if config.treat_zero_as_null and value == 0:
        return np.nan
    return value


def _normalise_series(series: pd.Series, config: ComparisonConfig) -> pd.Series:
    return series.map(lambda x: _normalise_value(x, config))


def _numeric_comparison(
    left: pd.Series,
    right: pd.Series,
    config: ComparisonConfig,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    left_num = pd.to_numeric(left, errors="coerce")
    right_num = pd.to_numeric(right, errors="coerce")
    comparable = left_num.notna() & right_num.notna()
    tolerance = config.absolute_tolerance + config.relative_tolerance * right_num.abs()
    tolerance = tolerance.fillna(config.absolute_tolerance)
    equal = (left_num - right_num).abs() <= tolerance
    return equal, left_num, right_num


def _datetime_comparison(
    left: pd.Series,
    right: pd.Series,
    config: ComparisonConfig,
) -> Optional[tuple[pd.Series, pd.Series]]:
    if config.datetime_tolerance is None:
        return None
    left_dt = pd.to_datetime(left, errors="coerce")
    right_dt = pd.to_datetime(right, errors="coerce")
    comparable = left_dt.notna() & right_dt.notna()
    if not comparable.any():
        return None
    diff = (left_dt - right_dt).abs()
    equal = pd.Series(False, index=left.index)
    equal.loc[comparable] = diff.loc[comparable] <= config.datetime_tolerance
    return equal, comparable


def compute_diff(
    left_df: pd.DataFrame,
    right_df: pd.DataFrame,
    *,
    join_keys: Sequence[str],
    mappings: Sequence[ColumnMapping],
    config: Optional[ComparisonConfig] = None,
) -> DiffResult:
    """Compare ``left_df`` and ``right_df`` using the provided configuration."""

    if config is None:
        config = ComparisonConfig()
    if (
        config.datetime_tolerance is not None
        and not isinstance(config.datetime_tolerance, pd.Timedelta)
    ):
        config.datetime_tolerance = pd.to_timedelta(config.datetime_tolerance)

    _ensure_columns(left_df, join_keys, "left")
    _ensure_columns(right_df, join_keys, "right")

    if left_df.duplicated(subset=list(join_keys)).any():
        raise ComparisonError("Left dataset contains duplicate join keys")
    if right_df.duplicated(subset=list(join_keys)).any():
        raise ComparisonError("Right dataset contains duplicate join keys")

    left_prepared = left_df[list(join_keys)].copy()
    right_prepared = right_df[list(join_keys)].copy()

    output_names: List[str] = []
    for mapping in mappings:
        alias = mapping.output_name()
        left_series = _materialise_columns(left_df, mapping.left, "left")
        right_series = _materialise_columns(right_df, mapping.right, "right")
        left_prepared[f"{alias}__left"] = left_series.values
        right_prepared[f"{alias}__right"] = right_series.values
        output_names.append(alias)

    merged = left_prepared.merge(
        right_prepared,
        on=list(join_keys),
        how="outer",
        indicator=True,
        suffixes=("__left", "__right"),
    )
    merged = merged.reset_index(drop=True)

    left_only = merged[merged["_merge"] == "left_only"].copy()
    right_only = merged[merged["_merge"] == "right_only"].copy()
    both = merged[merged["_merge"] == "both"].copy()

    if both.empty:
        return DiffResult(
            matched=pd.DataFrame(columns=merged.columns),
            mismatched=pd.DataFrame(columns=merged.columns),
            left_only=left_only.drop(columns=["_merge"]),
            right_only=right_only.drop(columns=["_merge"]),
            details=pd.DataFrame(columns=["column", "left_value", "right_value"]),
            config=config,
            mappings=list(mappings),
        )

    row_match_mask = pd.Series(True, index=both.index)
    detail_records: List[DifferenceRecord] = []

    for alias in output_names:
        left_col = f"{alias}__left"
        right_col = f"{alias}__right"
        left_values = _normalise_series(both[left_col], config)
        right_values = _normalise_series(both[right_col], config)

        numeric_equal, left_num, right_num = _numeric_comparison(left_values, right_values, config)
        datetime_result = _datetime_comparison(left_values, right_values, config)

        equality_mask = numeric_equal.copy()
        equality_mask = equality_mask.fillna(False)

        string_mask = ~(left_num.notna() & right_num.notna())
        str_equal = (left_values == right_values) | (left_values.isna() & right_values.isna())
        equality_mask.loc[string_mask] = str_equal.loc[string_mask].fillna(False)

        if datetime_result is not None:
            datetime_equal, comparable = datetime_result
            equality_mask.loc[comparable] = (
                equality_mask.loc[comparable] | datetime_equal.loc[comparable]
            )

        row_match_mask &= equality_mask

        mismatch_indices = equality_mask[~equality_mask].index
        for idx in mismatch_indices:
            keys = {key: both.at[idx, key] for key in join_keys}
            diff_value: Optional[float] = None
            diff_pct: Optional[float] = None
            if pd.notna(left_num.iat[idx]) and pd.notna(right_num.iat[idx]):
                diff_value = float(left_num.iat[idx] - right_num.iat[idx])
                if right_num.iat[idx] != 0:
                    diff_pct = diff_value / float(right_num.iat[idx])
            detail_records.append(
                DifferenceRecord(
                    keys=keys,
                    column=alias,
                    left_value=both.at[idx, left_col],
                    right_value=both.at[idx, right_col],
                    difference=diff_value,
                    difference_pct=diff_pct,
                )
            )

    matched = both[row_match_mask].copy()
    mismatched = both[~row_match_mask].copy()

    details_df = (
        pd.DataFrame(
            [
                {
                    **record.keys,
                    "column": record.column,
                    "left_value": record.left_value,
                    "right_value": record.right_value,
                    "difference": record.difference,
                    "difference_pct": record.difference_pct,
                }
                for record in detail_records
            ]
        )
        if detail_records
        else pd.DataFrame(
            columns=[*join_keys, "column", "left_value", "right_value", "difference", "difference_pct"]
        )
    )

    return DiffResult(
        matched=matched.drop(columns=["_merge"], errors="ignore"),
        mismatched=mismatched.drop(columns=["_merge"], errors="ignore"),
        left_only=left_only.drop(columns=["_merge"]),
        right_only=right_only.drop(columns=["_merge"]),
        details=details_df,
        config=config,
        mappings=list(mappings),
    )


__all__ = [
    "ColumnMapping",
    "ComparisonConfig",
    "ComparisonError",
    "DiffResult",
    "compute_diff",
]
