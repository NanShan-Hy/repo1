"""Column mapping recommendation heuristics."""
from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Dict, List, Mapping

import pandas as pd


@dataclass
class MappingCandidate:
    left: str
    right: str
    score: float
    reason: str

    def as_dict(self) -> Dict[str, object]:
        return {"left": self.left, "right": self.right, "score": self.score, "reason": self.reason}


def _normalise_label(label: str) -> str:
    return label.replace("_", " ").replace("-", " ").lower()


def _string_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalise_label(a), _normalise_label(b)).ratio()


def _value_overlap(left: pd.Series, right: pd.Series) -> float:
    left_sample = left.dropna().astype(str)
    right_sample = right.dropna().astype(str)
    if left_sample.empty or right_sample.empty:
        return 0.0
    left_unique = set(left_sample.sample(min(200, len(left_sample)), random_state=0))
    right_unique = set(right_sample.sample(min(200, len(right_sample)), random_state=0))
    intersection = left_unique.intersection(right_unique)
    union = left_unique.union(right_unique)
    return len(intersection) / len(union) if union else 0.0


def recommend_mappings(
    left_df: pd.DataFrame,
    right_df: pd.DataFrame,
    *,
    left_types: Mapping[str, str] | None = None,
    right_types: Mapping[str, str] | None = None,
    per_column: int = 3,
) -> Dict[str, List[MappingCandidate]]:
    """Return mapping suggestions for columns in ``left_df``."""

    suggestions: Dict[str, List[MappingCandidate]] = {}
    for left_col in left_df.columns:
        candidates: List[MappingCandidate] = []
        left_type = left_types.get(left_col) if left_types else None
        for right_col in right_df.columns:
            similarity = _string_similarity(left_col, right_col)
            overlap = _value_overlap(left_df[left_col], right_df[right_col])
            score = 0.7 * similarity + 0.3 * overlap
            reason_parts = [f"label={similarity:.2f}"]
            if overlap:
                reason_parts.append(f"overlap={overlap:.2f}")
            if left_type and right_types:
                right_type = right_types.get(right_col)
                if right_type and right_type != left_type:
                    score *= 0.85
                    reason_parts.append(f"type_penalty:{left_type}->{right_type}")
            candidates.append(
                MappingCandidate(
                    left=left_col,
                    right=right_col,
                    score=round(score, 4),
                    reason=", ".join(reason_parts),
                )
            )
        candidates.sort(key=lambda item: item.score, reverse=True)
        suggestions[left_col] = candidates[:per_column]
    return suggestions


__all__ = ["MappingCandidate", "recommend_mappings"]
