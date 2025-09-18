"""Public package interface for the data comparison toolkit."""
from .compare.diff import ColumnMapping, ComparisonConfig, DiffResult, compute_diff
from .dedup.dedup import DeduplicationResult, deduplicate

__all__ = [
    "ColumnMapping",
    "ComparisonConfig",
    "DiffResult",
    "DeduplicationResult",
    "compute_diff",
    "deduplicate",
]
